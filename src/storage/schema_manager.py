"""
图数据模型/Schema 管理模块

定义知识图谱的节点标签、关系类型、属性约束等 Schema 信息。
"""
import logging
from typing import Dict, List


class GraphSchema:
    """知识图谱 Schema 定义"""

    # ─── 节点类型 ────────────────────────────────────────────────────────
    NODE_LABELS = {
        "Equipment": {
            "description": "设备/装置",
            "properties": ["name", "status", "source"],
        },
        "Material": {
            "description": "物料/化学品",
            "properties": ["name", "cas_number", "property", "source"],
        },
        "Abnormal_Condition": {
            "description": "异常状态/事件",
            "properties": ["name", "description", "time", "source"],
        },
        "Consequence": {
            "description": "事故后果",
            "properties": ["name", "severity", "casualties", "source"],
        },
        "Mitigation": {
            "description": "应急/缓解措施",
            "properties": ["name", "action", "effectiveness", "source"],
        },
        "Accident": {
            "description": "事故案例",
            "properties": [
                "id", "title", "date", "location",
                "industry", "summary", "source",
            ],
        },
    }

    # ─── 关系类型 ────────────────────────────────────────────────────────
    RELATION_TYPES = {
        "leads_to": {
            "description": "因果关系 A → B",
            "properties": ["confidence", "source"],
        },
        "involves": {
            "description": "涉及某实体",
            "properties": ["role", "source"],
        },
        "mitigated_by": {
            "description": "被某措施缓解",
            "properties": ["effectiveness", "source"],
        },
        "occurs_at": {
            "description": "发生于 (地点/时间)",
            "properties": ["source"],
        },
        "has_property": {
            "description": "具有某属性",
            "properties": ["value", "unit", "source"],
        },
        "belongs_to": {
            "description": "属于某事故案例",
            "properties": ["source"],
        },
    }

    @classmethod
    def create_index_constraints(cls, neo4j_graph) -> List[str]:
        """
        在 Neo4j 中创建索引和唯一约束。

        为常用查询字段建立索引，按 name 建立唯一约束防止重复节点。
        """
        statements = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Equipment) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Material) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Accident) REQUIRE n.title IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (n:Abnormal_Condition) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Accident) ON (n.id)",
        ]
        executed = []
        for stmt in statements:
            try:
                neo4j_graph.run(stmt)
                executed.append(stmt)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"执行 Cypher 失败: {stmt[:60]}... -> {e}")
        return executed
