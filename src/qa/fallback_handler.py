"""
降级处理模块

当主流程 (LLM抽取/因果检索/LLM生成) 失败时的备选方案。
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class FallbackHandler:
    """降级处理器"""

    def text_search_fallback(
        self, question: str, text_index: Dict
    ) -> str:
        """
        降级方案: 当 Graph RAG 不可用时，退化为全文检索。

        TODO [完善]:
          1. 构建事故报告文本倒排索引
          2. 关键词匹配检索
          3. 返回匹配片段
        """
        # 简单的关键词匹配
        results = []
        for report_id, text in text_index.items():
            if any(kw in text for kw in question.split()):
                results.append(f"[{report_id}]: {text[:200]}...")

        if results:
            return "全文检索结果（降级模式）:\n" + "\n\n".join(results[:5])
        return "未找到相关信息。"

    def template_response(self, intent: str) -> str:
        """
        模板应答: 当完全无法获取信息时的友好提示。
        """
        messages = {
            "no_kg": (
                "知识图谱尚未构建完成。请先完成以下步骤：\n"
                "1. 运行数据采集流水线获取事故报告\n"
                "2. 运行 LLM 抽取流水线构建知识图谱\n"
                "3. 确保 Neo4j 服务已启动"
            ),
            "no_result": "未在知识图谱中检索到与您的问题相关的因果路径。请尝试更换关键词或提问方式。",
            "api_error": "大模型服务暂时不可用，请检查 API 配置和网络连接。",
        }
        return messages.get(intent, "系统暂时无法处理您的请求，请稍后再试。")
