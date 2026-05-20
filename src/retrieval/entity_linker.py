"""
实体链接模块

将用户问题中识别的实体与知识图谱中的节点进行匹配对齐。
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class EntityLinker:
    """实体链接器"""

    def __init__(self):
        # TODO [完善]: 加载知识图谱实体索引
        self.entity_index: Dict[str, str] = {}  # entity_name → node_type

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

        TODO [完善]:
          1. 精确匹配 → 模糊匹配 → 同义词匹配 三级策略
          2. 匹配结果的置信度评分
          3. 未匹配实体的处理 (提交 LLM 补充识别)
        """
        matched = []
        for name in entity_names:
            # 在 Neo4j 中模糊查询节点
            query = """
            MATCH (n) 
            WHERE n.name CONTAINS $name 
            RETURN n.name AS name, labels(n)[0] AS type 
            LIMIT 1
            """
            try:
                result = neo4j_client.graph.run(query, name=name).data()
                if result:
                    matched.append({
                        "name": result[0]["name"],
                        "type": result[0]["type"],
                        "matched": True,
                        "original_query": name
                    })
                else:
                    matched.append({
                        "name": name,
                        "type": "unknown",
                        "matched": False,
                    })
            except Exception as e:
                logger.error(f"实体链接查询失败: {e}")
                matched.append({"name": name, "type": "unknown", "matched": False})
        return matched
