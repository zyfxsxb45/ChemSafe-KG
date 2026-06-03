"""
因果路径检索模块

执行 Cypher 查询并将结果格式化为可供 LLM 阅读的上下文。
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class CausalPathRetriever:
    """因果路径检索器"""

    def __init__(self, neo4j_client):
        self.neo4j = neo4j_client

    def retrieve(
        self,
        entity_name: str,
        max_depth: int = 4,
    ) -> List[Dict]:
        """
        检索从指定实体出发的因果路径。

        Args:
            entity_name: 起始实体名
            max_depth: 因果链最大深度

        Returns:
            [{"node_names": ["A", "B", "C"], "rel_types": ["leads_to", ...]}, ...]
        """
        logger.info(f"检索因果路径: '{entity_name}', depth={max_depth}")
        paths = self.neo4j.find_causal_paths(entity_name, max_depth)
        return paths

    def format_context(self, paths: List[Dict]) -> str:
        """
        将图查询结果格式化为 LLM 可读的文本上下文。
        包含节点类型标签，便于 LLM 理解因果结构。
        """
        if not paths:
            return "未检索到相关因果路径。"

        context_parts = []
        context_parts.append(f"检索到 {len(paths)} 条因果链：\n")

        # 实体类型中文映射
        type_cn = {
            "Equipment": "设备", "Material": "物料",
            "Abnormal_Condition": "异常状态", "Consequence": "事故后果",
            "Mitigation": "应急措施", "Accident": "事故",
        }

        for i, path in enumerate(paths, 1):
            node_names = path.get("node_names", [])
            rel_types = path.get("rel_types", [])
            node_types = path.get("node_types", [])

            if not node_names:
                continue

            context_parts.append(f"【路径 {i}】(深度 {len(node_names)-1} 步)")
            for j in range(len(node_names)):
                ntype = node_types[j] if j < len(node_types) else ""
                type_tag = f" [{type_cn.get(ntype, ntype)}]" if ntype else ""
                context_parts.append(f"  ● {node_names[j]}{type_tag}")
                if j < len(rel_types):
                    rel_cn = {"leads_to": "导致", "involves": "涉及", "mitigated_by": "被缓解"}
                    context_parts.append(f"     ↓ {rel_cn.get(rel_types[j], rel_types[j])}")
            context_parts.append("")

        return "\n".join(context_parts)
