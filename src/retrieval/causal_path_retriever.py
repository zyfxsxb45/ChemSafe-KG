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

        输出格式:
          检索到 X 条因果链：

          路径 1: 设备故障 → 异常状态 → 事故后果
            - 冷却水循环泵
            ↓ leads_to
            - 储罐温度上升 (Abnormal_Condition)
            ...

        Args:
            paths: CausalPathRetriever.retrieve() 返回的路径列表

        Returns:
            格式化后的因果链文本
        """
        if not paths:
            return "未检索到相关因果路径。"

        context_parts = []
        context_parts.append(f"检索到 {len(paths)} 条因果链：\n")

        for i, path in enumerate(paths, 1):
            node_names = path.get("node_names", [])
            rel_types = path.get("rel_types", [])

            if not node_names:
                continue

            context_parts.append(f"【路径 {i}】(长度 {len(node_names)-1} 步)")
            for j in range(len(node_names)):
                context_parts.append(f"  ● {node_names[j]}")
                if j < len(rel_types):
                    context_parts.append(f"     ↓ {rel_types[j]}")
            context_parts.append("")  # 空行分隔

        return "\n".join(context_parts)
