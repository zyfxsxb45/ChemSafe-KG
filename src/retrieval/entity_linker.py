"""
实体链接模块

将用户问题中识别的实体与知识图谱中的节点进行匹配对齐。
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class EntityLinker:
    """实体链接器"""

    def __init__(self):
        # 实体索引由 link_entities() 动态从 Neo4j 加载
        self.entity_index: Dict[str, str] = {}

    def link_entities(
        self, entity_names: List[str], neo4j_client
    ) -> List[Dict]:
        """
        将实体名列表链接到图数据库中的节点。

        Args:
            entity_names: 待链接的实体名列表
            neo4j_client: Neo4j 客户端

        Returns:
            [{"name": "...", "type": "...", "matched": True}, ...]

        匹配策略:
          1. 精确匹配: n.name = query
          2. 包含匹配: n.name CONTAINS query
          3. 反向包含: query CONTAINS n.name
        """
        matched = []
        for name in entity_names:
            candidate = self._match_one(name, neo4j_client)
            if candidate:
                matched.append(candidate)
            else:
                matched.append({
                    "query": name,
                    "name": name,
                    "type": "unknown",
                    "matched": False,
                    "confidence": 0.0,
                    "match_type": "none",
                })
        return matched

    def _match_one(self, name: str, neo4j_client) -> Dict | None:
        """Find the best graph node for one entity mention."""
        cleaned = (name or "").strip()
        if not cleaned or neo4j_client.graph is None:
            return None

        query = """
        MATCH (n)
        WHERE n.name = $name
           OR n.name CONTAINS $name
           OR $name CONTAINS n.name
        WITH n,
             CASE
               WHEN n.name = $name THEN 3
               WHEN n.name CONTAINS $name THEN 2
               WHEN $name CONTAINS n.name THEN 1
               ELSE 0
             END AS score
        RETURN n.name AS name,
               labels(n)[0] AS type,
               score
        ORDER BY score DESC, size(n.name) ASC
        LIMIT 1
        """
        try:
            row = neo4j_client.graph.run(query, name=cleaned).data()
        except Exception as e:
            logger.warning(f"实体链接查询失败: {cleaned} -> {e}")
            return None

        if not row:
            return None

        result = row[0]
        score = result.get("score", 0)
        match_type = {
            3: "exact",
            2: "contains",
            1: "reverse_contains",
        }.get(score, "none")
        confidence = {
            3: 1.0,
            2: 0.75,
            1: 0.6,
        }.get(score, 0.0)

        return {
            "query": cleaned,
            "name": result.get("name", cleaned),
            "type": result.get("type", "unknown"),
            "matched": score > 0,
            "confidence": confidence,
            "match_type": match_type,
        }
