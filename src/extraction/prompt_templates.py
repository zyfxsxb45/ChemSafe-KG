"""
Prompt 模板管理模块

设计和管理用于知识抽取的 Prompt Chain（提示词链）。
包含 System Prompt、抽取指令、输出格式约束等。

TODO [完善]:
  1. 根据测试结果迭代优化 Prompt 模板
  2. 可考虑 Few-shot 示例的添加
  3. 支持中英文双语的 Prompt 版本
"""
from typing import List, Optional


class PromptTemplates:
    """Prompt 模板集合"""

    # ─── System Prompt: 角色设定 ────────────────────────────────────────
    SYSTEM_PROMPT = """你是一位化工过程安全专家。请阅读以下事故调查报告片段，识别其中包含的因果事件链。

实体类型定义：
- Equipment: 涉及的设备/装置 (如反应釜、储罐、管道、泵、阀门)
- Material: 涉及的化学品/物料 (如丙烯腈、苯、氯气)
- Abnormal_Condition: 异常状态/事件 (如温度升高、压力超标、泄漏)
- Consequence: 事故后果 (如爆炸、火灾、中毒、人员伤亡)
- Mitigation: 应急/缓解措施 (如启动喷淋系统、紧急停车)

关系类型：
- leads_to: A 导致 B（因果关系）
- involves: 涉及某设备或物料
- mitigated_by: 被某措施缓解

输出格式：严格的 JSON，包含以下字段：
- event_chain: 事件链列表，每个元素可以是实体定义或关系
- root_cause: 根原因总结
- consequence: 最终后果总结"""

    # ─── 抽取指令模板 ──────────────────────────────────────────────────
    EXTRACTION_TEMPLATE = """请分析以下事故报告片段，提取完整的因果事件链。

报告片段：
{report_text}

请严格按照 System Prompt 中的实体类型和关系类型进行抽取。
注意：
1. 每个事件链元素必须按实际时间/因果顺序排列
2. 同一实体在不同阶段出现时分别列出
3. 如果片段信息不足，只抽取明确提到的内容，不要臆测
4. 根原因(root_cause)应是整个事故链的起始故障

输出 JSON 结构：
{{
  "event_chain": [
    {{"entity": "...", "type": "Equipment|Material|Abnormal_Condition|Consequence|Mitigation", "status": "...", "action": "..."}},
    {{"relation": "leads_to|involves|mitigated_by", "target": "..."}},
    ...
  ],
  "root_cause": "string",
  "consequence": "string"
}}"""

    # ─── 质量验证 Prompt ──────────────────────────────────────────────
    VALIDATION_PROMPT = """请验证以下抽取结果是否满足要求：
1. 所有实体类型是否属于预定义类型
2. 因果链是否连续完整
3. JSON 格式是否正确

抽取结果：
{extraction_result}

如有问题请指出具体问题，如没有问题请回复 "VALID"。"""

    @classmethod
    def format_extraction_prompt(cls, report_text: str) -> str:
        """格式化抽取 Prompt"""
        return cls.EXTRACTION_TEMPLATE.format(report_text=report_text)

    # TODO [完善]: 可添加更多 Prompt 模板
    # - Few-shot Prompt (带示例的抽取)
    # - 多轮对话 Prompt Chain (逐步细化)
    # - 特定实体类型的专注抽取 Prompt
