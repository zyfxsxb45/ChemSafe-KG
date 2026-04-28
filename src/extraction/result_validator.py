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

    def validate_structure(self, result: Dict) -> bool:
        """
        验证抽取结果的 JSON 结构完整性。

        TODO [完善]:
          1. 检查 event_chain 是否为空
          2. 检查 root_cause 和 consequence 是否存在
          3. 检查实体类型是否属于预定义集合
        """
        if not result:
            return False
        if "event_chain" not in result:
            return False
        if "root_cause" not in result:
            return False
        if "consequence" not in result:
            return False
        return True

    def validate_entity_types(self, result: Dict) -> List[str]:
        """
        验证实体类型合法性，返回非法类型列表。

        TODO [完善]:
          1. 检查每个 entity 的 type 字段是否在允许范围内
          2. 自动修正常见拼写错误
        """
        valid_types = set(ext_config.ENTITY_TYPES)
        invalid = []
        for item in result.get("event_chain", []):
            if "entity" in item:
                etype = item.get("type", "")
                if etype not in valid_types:
                    invalid.append(etype)
        return invalid

    def calculate_confidence(self, result: Dict) -> float:
        """
        计算抽取结果的置信度评分。

        TODO [完善]:
          1. 基于链长度、实体类型覆盖率等维度评分
          2. 可引入 LLM 自评估 (让 LLM 给自己的抽取打分)
        """
        score = 1.0
        chain = result.get("event_chain", [])

        # 空链降分
        if not chain:
            return 0.0

        # 链过短可能信息不完整
        if len(chain) < 2:
            score *= 0.6

        # 缺少根原因或后果降分
        if not result.get("root_cause"):
            score *= 0.8
        if not result.get("consequence"):
            score *= 0.8

        return round(score, 2)
