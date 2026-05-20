"""
Neo4j 图数据库客户端

封装 Neo4j 的连接管理和知识图谱的写入/查询操作。
Neo4j 版本: 5.26.25 (社区版)
连接配置在 .env: NEO4J_URI / USER / PASSWORD
"""
import logging
from typing import List, Dict, Optional
from py2neo import Graph, Node, Relationship
from config.settings import neo4j as neo4j_config

logger = logging.getLogger(__name__)


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
        rel = Relationship(source, rel_type, target, **(properties or {}))
        self.graph.create(rel)

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
        
        # 开启事务批量提交，大幅减少网络 I/O 开销
        tx = self.graph.begin()
        
        for subj, rel, obj in triples:
            subj_type = entity_type_map.get(subj, "Abnormal_Condition")
            obj_type = entity_type_map.get(obj, "Abnormal_Condition")

            subj_node = Node(subj_type, name=subj)
            obj_node = Node(obj_type, name=obj)
            
            tx.merge(subj_node, subj_type, "name")
            tx.merge(obj_node, obj_type, "name")

            rel_obj = Relationship(subj_node, rel, obj_node, source=source_report)
            tx.create(rel_obj)
            
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
            # 参数化查询: 先匹配起始节点，再遍历因果链
            query = f"""
            MATCH path = (start {{name: $name}})
                          -[:leads_to|involves|mitigated_by*1..{max_depth}]->(end)
            RETURN [n in nodes(path) | n.name] AS node_names,
                   [r in relationships(path) | type(r)] AS rel_types,
                   length(path) AS path_len
            ORDER BY path_len ASC
            LIMIT 10
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
            data = self.graph.run(
                "MATCH (n) RETURN n.name AS name LIMIT 500"
            ).data()
            return [str(row["name"]) for row in data if row.get("name") is not None]
        except Exception:
            return []

    def get_entity_count(self) -> int:
        """获取实体总数"""
        data = self.graph.run("MATCH (n) RETURN count(n) AS c").data()
        return data[0]["c"] if data else 0

    def get_relation_count(self) -> int:
        """获取关系总数"""
        data = self.graph.run("MATCH ()-[r]->() RETURN count(r) AS c").data()
        return data[0]["c"] if data else 0

    def clear_all(self):
        """清空图数据库 (开发测试用)"""
        self.graph.delete_all()
        logger.info("已清空 Neo4j 图数据库")
