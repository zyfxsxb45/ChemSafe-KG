"""
自然语言查询分析模块

解析用户输入的自然语言问题，识别查询意图和关键实体。
"""
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """NL查询分析器"""

    # 化工安全领域的关键词表
    # TODO [完善]: 根据实际查询需求扩充
    INTENT_KEYWORDS = {
        "causal_chain": ["原因", "导致", "引发", "怎样发生", "事故经过", "如何演变成"],
        "risk_factor": ["风险", "危险", "隐患", "不安全"],
        "mitigation": ["措施", "应急", "救援", "预防", "如何避免"],
        "chemical_property": ["物性", "性质", "闪点", "沸点", "爆炸极限"],
        "statistics": ["统计", "趋势", "分布", "最多", "常见"],
    }

    def analyze(self, question: str) -> Dict:
        """
        分析用户问题，返回结构化的查询意图。

        Args:
            question: 用户自然语言问题

        Returns:
            {
                "intent": "causal_chain",      # 查询意图
                "entities": ["丙烯腈", "储罐"], # 识别到的实体
                "constraints": {...},           # 约束条件
            }

        TODO [完善]:
          1. 使用 jieba 分词提取关键词
          2. 实体识别与对齐
          3. 时间/地点约束提取
        """
        intent = self._detect_intent(question)
        entities = self._extract_entities(question)

        return {
            "intent": intent,
            "entities": entities,
            "original_question": question,
        }

    def _detect_intent(self, question: str) -> str:
        """检测查询意图类型"""
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in question:
                    return intent
        return "causal_chain"  # 默认: 因果链查询

    def _extract_entities(self, question: str) -> List[str]:
        """
        从问题中提取化工安全领域的实体。

        TODO [完善]:
          1. 使用 jieba 分词 + 自定义词典
          2. 匹配知识图谱中已有的实体名
          3. 支持同义词扩展 (如 "丙烯腈" ↔ "AN")
        """
        # import jieba
        # words = jieba.lcut(question)
        # 与 KG 中的实体名进行匹配...
        return []
