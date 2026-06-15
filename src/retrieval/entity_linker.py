"""
实体链接模块

将用户问题中识别的实体与知识图谱中的节点进行匹配对齐。
"""
import logging
from typing import List, Dict, Callable, Optional
from src.retrieval.entity_normalizer import EntityNormalizer

logger = logging.getLogger(__name__)


class EntityLinker:
    """实体链接器"""

    def __init__(self):
        # 实体索引由 link_entities() 动态从 Neo4j 加载
        self.entity_index: Dict[str, str] = {}
        self._all_entities: List[Dict] = []
        self._loaded = False
        self.normalizer = EntityNormalizer()

    def _load_entities(self, neo4j_client):
        if self._loaded or neo4j_client.graph is None:
            return
        try:
            # 一次性加载所有实体及其类型到内存
            data = neo4j_client.graph.run(
                "MATCH (n) WHERE n.name IS NOT NULL AND size(labels(n)) > 0 "
                "WITH n, labels(n)[0] AS label "
                "WHERE label IN ['Equipment', 'Material', 'Abnormal_Condition', 'Consequence', 'Mitigation', 'Accident'] "
                "RETURN n.name AS name, label AS type"
            ).data()
            self._all_entities = [
                {
                    "name": str(row["name"]),
                    "type": str(row["type"]),
                    "normalized": self.normalizer.normalize(str(row["name"])),
                }
                for row in data
            ]
            self._loaded = True
            logger.info(f"已加载 {len(self._all_entities)} 个实体到内存用于快速链接")
        except Exception as e:
            logger.warning(f"加载实体索引失败: {e}")

    def link_entities(
        self, entity_names: List[str], neo4j_client,
        progress_callback: Optional[Callable[[str], None]] = None
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
        if progress_callback:
            progress_callback("正在加载知识图谱实体索引...")
        self._load_entities(neo4j_client)

        matched = []
        for name in entity_names:
            if progress_callback:
                progress_callback(f"正在匹配实体: '{name}' ...")
            candidate = self._match_one(name)
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

    def _match_one(self, name: str) -> Dict | None:
        """Find the best graph node for one entity mention."""
        cleaned = (name or "").strip()
        if not cleaned:
            return None
        normalized_query = self.normalizer.normalize(cleaned)

        best_match = None
        best_score = 0
        best_len = float('inf')

        for ent in self._all_entities:
            ent_name = ent["name"]
            ent_normalized = ent.get("normalized") or self.normalizer.normalize(ent_name)
            if ent_name == cleaned:
                score = 4
            elif ent_normalized and ent_normalized == normalized_query:
                score = 3
            elif cleaned in ent_name:
                score = 2
            elif ent_name in cleaned or (ent_normalized and ent_normalized in normalized_query):
                score = 1
            else:
                continue

            # 优先高分；同分时优先长度更短的（更精确）
            if score > best_score or (score == best_score and len(ent_name) < best_len):
                best_score = score
                best_match = ent
                best_len = len(ent_name)
                if score == 3:
                    break  # 找到精确匹配，直接返回

        if not best_match:
            return None

        match_type = {
            4: "exact",
            3: "normalized",
            2: "contains",
            1: "reverse_contains",
        }.get(best_score, "none")
        confidence = {
            4: 1.0,
            3: 0.9,
            2: 0.75,
            1: 0.6,
        }.get(best_score, 0.0)

        return {
            "query": cleaned,
            "name": best_match["name"],
            "type": best_match["type"],
            "matched": True,
            "confidence": confidence,
            "match_type": match_type,
        }
