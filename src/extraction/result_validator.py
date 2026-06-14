"""
抽取结果验证与质量评估模块

对 LLM 抽取的结构化结果进行自动化验证和质量评估。
"""
import logging
from typing import Dict, List
from config.settings import extraction as ext_config

logger = logging.getLogger(__name__)


class ResultValidator:
    """抽取结果验证器"""

    ENTITY_TYPE_ALIASES = {
        "Abnormal": "Abnormal_Condition",
        "AbnormalCondition": "Abnormal_Condition",
        "abnormal_condition": "Abnormal_Condition",
        "equipment": "Equipment",
        "material": "Material",
        "consequence": "Consequence",
        "mitigation": "Mitigation",
    }

    RELATION_ALIASES = {
        "cause": "leads_to",
        "causes": "leads_to",
        "lead_to": "leads_to",
        "leads": "leads_to",
        "include": "involves",
        "includes": "involves",
        "related_to": "involves",
        "mitigate": "mitigated_by",
        "mitigates": "mitigated_by",
    }

    def validate_structure(self, result: Dict) -> bool:
        """
        验证抽取结果的 JSON 结构完整性。
        """
        if not isinstance(result, dict):
            return False

        chain = result.get("event_chain")
        if not isinstance(chain, list) or not chain:
            return False

        if not str(result.get("root_cause", "")).strip():
            return False
        if not str(result.get("consequence", "")).strip():
            return False

        has_entity = False
        has_relation = False
        for item in chain:
            if not isinstance(item, dict):
                return False

            if "entity" in item:
                has_entity = True
                if not str(item.get("entity", "")).strip():
                    return False
                if self._normalize_entity_type(item.get("type")) not in ext_config.ENTITY_TYPES:
                    return False

            if "relation" in item:
                has_relation = True
                if self._normalize_relation(item.get("relation")) not in ext_config.RELATION_TYPES:
                    return False
                if not str(item.get("target") or item.get("object") or "").strip():
                    return False

            if "entity" not in item and "relation" not in item:
                return False

        if not has_entity or not has_relation:
            return False

        return True

    def validate_entity_types(self, result: Dict) -> List[str]:
        """
        验证实体类型合法性，返回非法类型列表。
        """
        valid_types = set(ext_config.ENTITY_TYPES)
        invalid = set()
        for item in result.get("event_chain", []):
            if isinstance(item, dict) and "entity" in item:
                etype = self._normalize_entity_type(item.get("type"))
                if etype not in valid_types:
                    invalid.add(str(item.get("type", "")).strip())
        return sorted(invalid)

    def validate_relation_types(self, result: Dict) -> List[str]:
        """验证关系类型合法性，返回非法关系类型列表。"""
        valid_relations = set(ext_config.RELATION_TYPES)
        invalid = set()
        for item in result.get("event_chain", []):
            if isinstance(item, dict) and "relation" in item:
                relation = self._normalize_relation(item.get("relation"))
                if relation not in valid_relations:
                    invalid.add(str(item.get("relation", "")).strip())
        return sorted(invalid)

    def normalize_result(self, result: Dict) -> Dict:
        """标准化常见实体/关系别名，返回新的结果字典。"""
        normalized = dict(result or {})
        normalized_chain = []
        for item in normalized.get("event_chain", []):
            if not isinstance(item, dict):
                normalized_chain.append(item)
                continue

            normalized_item = dict(item)
            if "type" in normalized_item:
                normalized_item["type"] = self._normalize_entity_type(normalized_item.get("type"))
            if "relation" in normalized_item:
                normalized_item["relation"] = self._normalize_relation(normalized_item.get("relation"))
            normalized_chain.append(normalized_item)

        normalized["event_chain"] = normalized_chain
        return normalized

    def calculate_confidence(self, result: Dict) -> float:
        """
        计算抽取结果的置信度评分。
        """
        if not isinstance(result, dict):
            return 0.0

        score = 1.0 if self.validate_structure(result) else 0.5
        chain = result.get("event_chain", [])

        if not isinstance(chain, list) or not chain:
            return 0.0

        entity_count = sum(1 for item in chain if isinstance(item, dict) and item.get("entity"))
        relation_count = sum(1 for item in chain if isinstance(item, dict) and item.get("relation"))

        if entity_count < 2:
            score *= 0.6
        if relation_count < 1:
            score *= 0.6
        if len(chain) < 5:
            score *= 0.85

        if not result.get("root_cause"):
            score *= 0.8
        if not result.get("consequence"):
            score *= 0.8
        if self.validate_entity_types(result):
            score *= 0.7
        if self.validate_relation_types(result):
            score *= 0.7

        return round(score, 2)

    def _normalize_entity_type(self, value) -> str:
        value = str(value or "").strip()
        return self.ENTITY_TYPE_ALIASES.get(value, self.ENTITY_TYPE_ALIASES.get(value.lower(), value))

    def _normalize_relation(self, value) -> str:
        value = str(value or "").strip()
        return self.RELATION_ALIASES.get(value.lower(), value)
