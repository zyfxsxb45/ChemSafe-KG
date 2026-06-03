"""
Neo4j 图数据库客户端

封装 Neo4j 的连接管理和知识图谱的写入/查询操作。
Neo4j 版本: 5.26.25 (社区版)
连接配置在 .env: NEO4J_URI / USER / PASSWORD
"""
import logging
from typing import List, Dict, Optional
from py2neo import Graph, Node
from config.settings import neo4j as neo4j_config
from config.settings import extraction as extraction_config
from src.storage.schema_manager import GraphSchema

logger = logging.getLogger(__name__)


ALLOWED_NODE_LABELS = set(GraphSchema.NODE_LABELS)
ALLOWED_RELATION_TYPES = set(GraphSchema.RELATION_TYPES) | set(extraction_config.RELATION_TYPES)


def _safe_label(label: str) -> str:
    """Return a Neo4j label after checking it against the project schema."""
    if label not in ALLOWED_NODE_LABELS:
        return "Abnormal_Condition"
    return label


def _safe_relation_type(rel_type: str) -> str:
    """Return a Neo4j relationship type after checking it against the schema."""
    if rel_type not in ALLOWED_RELATION_TYPES:
        return "leads_to"
    return rel_type


def _cypher_name(name: str) -> str:
    """Quote a schema-validated label or relationship type for Cypher."""
    return f"`{name}`"


class Neo4jClient:
    """Neo4j 图数据库客户端"""

    def __init__(self):
        self.graph: Optional[Graph] = None

    def connect(self):
        """建立 Neo4j 连接"""
        try:
            self.graph = Graph(
                neo4j_config.URI,
                auth=(neo4j_config.USER, neo4j_config.PASSWORD),
            )
            logger.info(f"已连接到 Neo4j: {neo4j_config.URI}")
        except Exception as e:
            logger.error(f"Neo4j 连接失败: {e}")
            logger.warning("请确保 Neo4j 服务已启动并在 .env 中正确配置")

    def create_entity_node(self, entity: Dict) -> Node:
        """
        创建实体节点，使用 MERGE 避免违反 UNIQUE 约束。

        Args:
            entity: {"name": str, "type": str, "properties": dict}

        Returns:
            Neo4j Node 对象
        """
        node = Node(
            entity["type"],
            name=entity["name"],
            **entity.get("properties", {}),
        )
        self.graph.merge(node, entity["type"], "name")
        return node

    def create_causal_relation(
        self,
        source: Node,
        target: Node,
        rel_type: str = "leads_to",
        properties: Optional[Dict] = None,
    ):
        """
        创建因果关系边。

        Args:
            source: 起始节点
            target: 目标节点
            rel_type: 关系类型 (默认 leads_to)
            properties: 关系属性 (如置信度、来源报告等)
        """
        props = properties or {}
        source_name = source.get("name")
        target_name = target.get("name")
        if not source_name or not target_name:
            logger.warning("跳过关系写入: 起点或终点缺少 name")
            return

        source_label = _safe_label(next(iter(source.labels), "Abnormal_Condition"))
        target_label = _safe_label(next(iter(target.labels), "Abnormal_Condition"))
        rel_type = _safe_relation_type(rel_type)
        source_report = props.get("source", "")

        query = f"""
        MERGE (s:{_cypher_name(source_label)} {{name: $source_name}})
        MERGE (t:{_cypher_name(target_label)} {{name: $target_name}})
        MERGE (s)-[r:{_cypher_name(rel_type)} {{source: $source_report}}]->(t)
        SET r += $props
        """
        self.graph.run(
            query,
            source_name=source_name,
            target_name=target_name,
            source_report=source_report,
            props=props,
        )

    def batch_create_triples(
        self,
        triples: List[tuple],
        entity_type_map: Optional[Dict[str, str]] = None,
        source_report: str = "",
    ):
        """
        批量创建三元组 (实体-关系-实体)，使用事务 (Transaction) 加速写入。

        Args:
            triples: [(subject, relation, object), ...]
            entity_type_map: {实体名: 实体类型} 映射
            source_report: 来源报告标识
        """
        if not triples:
            return

        entity_type_map = entity_type_map or {}
        
        tx = self.graph.begin()
        
        for subj, rel, obj in triples:
            if not subj or not obj:
                continue

            subj_type = _safe_label(entity_type_map.get(subj, "Abnormal_Condition"))
            obj_type = _safe_label(entity_type_map.get(obj, "Abnormal_Condition"))
            rel_type = _safe_relation_type(rel)

            query = f"""
            MERGE (s:{_cypher_name(subj_type)} {{name: $subj}})
            MERGE (o:{_cypher_name(obj_type)} {{name: $obj}})
            MERGE (s)-[r:{_cypher_name(rel_type)} {{source: $source_report}}]->(o)
            ON CREATE SET r.created_at = datetime()
            SET r.updated_at = datetime()
            """
            tx.run(query, subj=subj, obj=obj, source_report=source_report)
            
        tx.commit()

        logger.info(
            f"已批量写入 {len(triples)} 条三元组到 Neo4j "
            f"(实体类型: {set(entity_type_map.values())})"
        )

    def find_causal_paths(
        self,
        source_entity: str,
        max_depth: int = 4,
    ) -> List[Dict]:
        """
        查询从指定实体出发的因果路径。

        Args:
            source_entity: 起始实体名称
            max_depth: 因果链最大深度

        Returns:
            [{"node_names": ["A", "B", "C"], "rel_types": ["leads_to", "leads_to"]}, ...]
            按路径长度升序排列，最多返回 10 条
        """
        try:
            # 参数化查询: 以目标实体为中心，向前后双向扩展，查找最完整的因果链
            query = f"""
            MATCH path = (start)-[:leads_to|involves|mitigated_by*0..{max_depth}]->(mid {{name: $name}})-[:leads_to|involves|mitigated_by*0..{max_depth}]->(end)
            WHERE length(path) > 0
            RETURN [n in nodes(path) | n.name] AS node_names,
                   [n in nodes(path) | labels(n)[0]] AS node_types,
                   [r in relationships(path) | type(r)] AS rel_types,
                   length(path) AS path_len
            ORDER BY path_len DESC
            LIMIT 50
            """
            data = self.graph.run(query, name=source_entity).data()
            logger.info(f"查询因果路径: '{source_entity}' → 找到 {len(data)} 条")
            return data

        except Exception as e:
            logger.error(f"因果路径查询失败: {e}")
            return []

    def get_all_entity_names(self) -> List[str]:
        """获取知识图谱中所有实体名称（用于实体链接）"""
        try:
            # 只返回 ChemSafe-KG 定义的实体类型，排除其他项目的数据
            data = self.graph.run(
                "MATCH (n) WHERE n.name IS NOT NULL AND size(labels(n)) > 0 "
                "WITH n, labels(n)[0] AS label "
                "WHERE label IN ['Equipment', 'Material', 'Abnormal_Condition', 'Consequence', 'Mitigation', 'Accident'] "
                "RETURN n.name AS name LIMIT 500"
            ).data()
            return [str(row["name"]) for row in data if row.get("name") is not None]
        except Exception:
            return []

    def get_graph_snapshot(self, limit: int = 200) -> Dict[str, List[Dict]]:
        """
        获取用于前端展示的图谱快照。

        Returns:
            {
                "nodes": [{"id": "...", "label": "...", "group": "..."}],
                "edges": [{"from": "...", "to": "...", "label": "..."}],
            }
        """
        query = """
        MATCH (n)
        WHERE size(labels(n)) > 0
        WITH n, labels(n)[0] AS label
        WHERE label IN ['Equipment', 'Material', 'Abnormal_Condition', 'Consequence', 'Mitigation', 'Accident']
        ORDER BY coalesce(n.name, elementId(n))
        LIMIT $limit
        WITH collect(n) AS nodes
        OPTIONAL MATCH (a)-[r]->(b)
        WHERE a IN nodes AND b IN nodes
        RETURN
          [n IN nodes | {
            id: elementId(n),
            label: coalesce(n.name, elementId(n)),
            group: coalesce(labels(n)[0], "Entity"),
            title: coalesce(n.name, elementId(n))
          }] AS nodes,
          [rel IN collect({a: a, r: r, b: b})
           WHERE rel.r IS NOT NULL | {
            from: elementId(rel.a),
            to: elementId(rel.b),
            label: type(rel.r),
            title: coalesce(rel.r.source, "")
          }] AS edges
        """
        try:
            data = self.graph.run(query, limit=limit).data()
            if not data:
                return {"nodes": [], "edges": []}
            return {
                "nodes": data[0].get("nodes", []),
                "edges": data[0].get("edges", []),
            }
        except Exception as e:
            logger.error(f"获取图谱快照失败: {e}")
            return {"nodes": [], "edges": []}

    def get_entity_count(self) -> int:
        """获取实体总数（仅限 ChemSafe-KG 定义的实体类型）"""
        data = self.graph.run(
            "MATCH (n) WHERE size(labels(n)) > 0 "
            "WITH n, labels(n)[0] AS label "
            "WHERE label IN ['Equipment', 'Material', 'Abnormal_Condition', 'Consequence', 'Mitigation', 'Accident'] "
            "RETURN count(n) AS c"
        ).data()
        return data[0]["c"] if data else 0

    def get_relation_count(self) -> int:
        """获取关系总数"""
        data = self.graph.run("MATCH ()-[r]->() RETURN count(r) AS c").data()
        return data[0]["c"] if data else 0

    def clear_all(self):
        """清空图数据库 (开发测试用)"""
        self.graph.delete_all()
        logger.info("已清空 Neo4j 图数据库")
