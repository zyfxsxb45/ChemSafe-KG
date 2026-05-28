"""
实体关系抽取引擎

协调 LLM 调用和结果解析，将非结构化文本转换为结构化三元组。
"""
import json
import logging
from typing import List, Dict, Optional
from config.settings import extraction as extraction_config
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
                system_prompt=self.templates.get_system_prompt_with_rules(),
                user_prompt=prompt,
            )
            # 防御性过滤：删除 LLM 产生的非法实体类型
            if result and "event_chain" in result:
                from config.settings import extraction as ext_config
                valid_types = set(ext_config.ENTITY_TYPES)
                filtered = []
                for item in result["event_chain"]:
                    if isinstance(item, dict) and "entity" in item:
                        etype = item.get("type", "")
                        if etype not in valid_types:
                            continue  # 跳过非法类型的实体
                    filtered.append(item)
                result["event_chain"] = filtered
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

        支持两类常见 LLM 输出:
          1. {"entity": "A"} 后跟 {"relation": "leads_to", "target": "B"}
          2. {"source": "A", "relation": "leads_to", "target": "B"}

        会过滤字段缺失、未知关系类型和自环，并保持原始顺序去重。
        """
        valid_relations = set(extraction_config.RELATION_TYPES)
        triples = []
        seen = set()
        chain = extraction_result.get("event_chain", [])
        current_entity = None

        if not isinstance(chain, list):
            logger.warning("抽取结果 event_chain 不是列表，无法转换三元组")
            return []

        def normalize_text(value) -> str:
            if value is None:
                return ""
            return str(value).strip()

        def add_triple(subject, relation, target):
            subject = normalize_text(subject)
            relation = normalize_text(relation)
            target = normalize_text(target)

            if not subject or not relation or not target:
                return
            if relation not in valid_relations:
                logger.debug(f"跳过未知关系类型: {relation}")
                return
            if subject == target:
                logger.debug(f"跳过自环三元组: {subject} -[{relation}]-> {target}")
                return

            key = (subject, relation, target)
            if key in seen:
                return
            seen.add(key)
            triples.append(key)

        for item in chain:
            if not isinstance(item, dict):
                continue

            if "entity" in item:
                current_entity = normalize_text(item.get("entity"))

            if "relation" not in item:
                continue

            subject = item.get("source") or item.get("subject") or current_entity
            target = item.get("target") or item.get("object")
            add_triple(subject, item.get("relation"), target)

        return triples
