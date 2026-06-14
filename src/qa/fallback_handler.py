"""
降级处理模块

当主流程 (LLM抽取/因果检索/LLM生成) 失败时的备选方案。
"""
import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)


class FallbackHandler:
    """降级处理器"""

    STOP_WORDS = {"什么", "为什么", "如何", "怎么", "哪些", "有关", "事故", "导致"}
    DOMAIN_TERMS = [
        "硫化氢", "一氧化碳", "氯气", "氨", "苯", "甲醇", "乙炔", "氢气",
        "泄漏", "爆炸", "火灾", "中毒", "窒息", "腐蚀", "超温", "超压",
        "阀门", "管道", "储罐", "反应釜", "泵", "应急", "喷淋", "疏散",
    ]

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
        keywords = self._extract_keywords(question)
        if not keywords:
            return "未找到相关信息。"

        scored_results = []
        for report_id, text in text_index.items():
            text = str(text)
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored_results.append((score, str(report_id), text[:200]))

        if scored_results:
            scored_results.sort(key=lambda item: (-item[0], item[1]))
            results = [
                f"[{report_id}] 命中{score}个关键词: {snippet}..."
                for score, report_id, snippet in scored_results[:5]
            ]
            return "全文检索结果（降级模式）:\n" + "\n\n".join(results)
        return "未找到相关信息。"

    def _extract_keywords(self, question: str) -> list[str]:
        """从中文/英文问题中提取降级检索关键词。"""
        question = question or ""
        tokens = [term for term in self.DOMAIN_TERMS if term in question]
        tokens.extend(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", question))
        keywords = []
        seen = set()
        for token in tokens:
            if token in self.STOP_WORDS or token in seen:
                continue
            seen.add(token)
            keywords.append(token)
        return keywords

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
