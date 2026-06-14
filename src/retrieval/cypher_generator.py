"""
Cypher 查询语句生成模块

根据查询分析结果，动态生成 Cypher 查询语句。
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class CypherGenerator:
    """Cypher 查询生成器"""

    MAX_DEPTH = 8
    MAX_LIMIT = 100

    def generate(self, query_analysis: Dict) -> str:
        """
        根据查询分析结果生成 Cypher 语句。

        Args:
            query_analysis: QueryAnalyzer 的输出

        Returns:
            Cypher 查询语句

        TODO [完善]:
          1. 不同类型查询的模板化生成
          2. 路径长度自适应
          3. 查询参数化防注入
        """
        intent = query_analysis.get("intent")
        entities = query_analysis.get("entities", [])

        if intent == "causal_chain" and entities:
            return self._causal_chain_query(entities[0])
        if intent == "mitigation" and entities:
            return self._mitigation_query(entities[0])
        if intent == "statistics":
            return self._statistics_query(query_analysis.get("constraints", {}))

        # 默认兜底: 全图检索
        return self._fallback_query(entities)

    def _causal_chain_query(self, entity_name: str, max_depth: int = 4) -> str:
        """生成因果链查询"""
        entity_name = self._cypher_string(entity_name)
        max_depth = self._clamp_int(max_depth, default=4, minimum=1, maximum=self.MAX_DEPTH)
        return f"""
        MATCH path = (start {{name: {entity_name}}})
                      -[:leads_to*1..{max_depth}]->(end:Consequence)
        RETURN path
        LIMIT 10
        """

    def _mitigation_query(self, entity_name: str) -> str:
        """生成缓解措施查询：查找导致该后果的异常状态及对应的缓解措施"""
        entity_name = self._cypher_string(entity_name)
        return f"""
        MATCH (cause)-[:leads_to*1..3]->(target {{name: {entity_name}}})
        OPTIONAL MATCH (cause)-[:mitigated_by]->(mitigation:Mitigation)
        RETURN cause.name AS risk, mitigation.name AS measure, type(mitigation) AS mitigation_type
        LIMIT 10
        """

    def _statistics_query(self, constraints: Dict) -> str:
        """生成统计分析查询：按约束条件聚合"""
        group_by = constraints.get("group_by", "type")
        limit = self._clamp_int(
            constraints.get("limit", 20),
            default=20,
            minimum=1,
            maximum=self.MAX_LIMIT,
        )
        if group_by == "type":
            return f"""
            MATCH (n)
            WHERE size(labels(n)) > 0
            WITH labels(n)[0] AS node_type, count(*) AS cnt
            WHERE node_type IN ['Equipment','Material','Abnormal_Condition','Consequence','Mitigation','Accident']
            RETURN node_type, cnt
            ORDER BY cnt DESC
            LIMIT {limit}
            """
        elif group_by == "relation":
            return f"""
            MATCH ()-[r]->()
            RETURN type(r) AS rel_type, count(*) AS cnt
            ORDER BY cnt DESC
            LIMIT {limit}
            """
        return f"MATCH (n) RETURN labels(n)[0] AS type, count(*) AS cnt ORDER BY cnt DESC LIMIT {limit}"

    def _fallback_query(self, entities: List[str]) -> str:
        """兜底查询"""
        if entities:
            entity = self._cypher_string(entities[0])
            return f"MATCH (n) WHERE n.name CONTAINS {entity} RETURN n LIMIT 20"
        return "MATCH (n) RETURN n LIMIT 50"

    def _cypher_string(self, value: str) -> str:
        """将用户输入转为 Cypher 字符串字面量，避免破坏查询结构。"""
        escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

    def _clamp_int(
        self,
        value,
        default: int,
        minimum: int,
        maximum: int,
    ) -> int:
        """将外部输入限制到安全的整数范围。"""
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, parsed))
