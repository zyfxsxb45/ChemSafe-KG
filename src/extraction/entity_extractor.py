"""
实体关系抽取引擎

协调 LLM 调用和结果解析，将非结构化文本转换为结构化三元组。
"""
import json
import logging
from typing import List, Dict, Optional
from src.extraction.llm_client import LLMClient
from src.extraction.prompt_templates import PromptTemplates

logger = logging.getLogger(__name__)


class EntityExtractor:
    """实体关系抽取器"""

    def __init__(self):
        self.llm = LLMClient()
        self.templates = PromptTemplates()

    def extract_from_text(self, report_text: str) -> Optional[Dict]:
        """
        从单段报告文本中提取因果事件链。

        Args:
            report_text: 清洗后的事故报告文本片段

        Returns:
            结构化的抽取结果:
            {
                "event_chain": [...],
                "root_cause": "...",
                "consequence": "..."
            }

        TODO [完善]:
          1. 对超长文本进行分段抽取后合并
          2. 多轮抽取: 先抽实体再抽关系
          3. 一致性校验: 确保跨片段的实体引用一致
        """
        prompt = self.templates.format_extraction_prompt(report_text)

        try:
            result = self.llm.chat_json(
                system_prompt=self.templates.SYSTEM_PROMPT,
                user_prompt=prompt,
            )
            return result
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"抽取结果解析失败: {e}")
            return None

    def extract_batch(
        self, text_chunks: List[str]
    ) -> List[Dict]:
        """
        批量抽取多个文本片段。

        Args:
            text_chunks: 文本片段列表

        Returns:
            抽取结果列表

        TODO [完善]:
          1. 并发调用 LLM API 加速
          2. 抽取结果的去重与合并
          3. 跨片段实体对齐
        """
        results = []
        for i, chunk in enumerate(text_chunks):
            logger.info(f"抽取第 {i + 1}/{len(text_chunks)} 段...")
            result = self.extract_from_text(chunk)
            if result:
                results.append(result)
        return results

    def convert_to_triples(
        self, extraction_result: Dict
    ) -> List[tuple]:
        """
        将抽取结果转换为 (subject, relation, object) 三元组格式。

        TODO [完善]:
          1. 正确处理 event_chain 中的实体和关系交替
          2. 为每个实体添加类型标签
          3. 去重逻辑
        """
        triples = []
        chain = extraction_result.get("event_chain", [])
        current_entity = None

        for item in chain:
            if "entity" in item:
                current_entity = item["entity"]
            elif "relation" in item and current_entity:
                triples.append((
                    current_entity,
                    item["relation"],
                    item["target"],
                ))

        return triples
