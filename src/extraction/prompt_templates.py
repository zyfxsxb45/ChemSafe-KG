"""
Prompt 模板管理模块

设计和管理用于知识抽取的 Prompt Chain（提示词链）。
包含 System Prompt、Few-shot 示例、抽取指令、输出格式约束等。
"""
from typing import List, Optional


# 允许的实体类型 —— 与 settings.py ExtractionConfig.ENTITY_TYPES 同步
ALLOWED_ENTITY_TYPES = {"Equipment", "Material", "Abnormal_Condition", "Consequence", "Mitigation"}


class PromptTemplates:
    """Prompt 模板集合"""

    # ─── System Prompt: 角色设定 ────────────────────────────────────────
    SYSTEM_PROMPT = """你是一位化工过程安全专家。请阅读以下事故调查报告片段，识别其中包含的因果事件链。

## 实体类型

必须且只能使用以下 5 种实体类型，不得创建其他类型（例如不允许使用 Event、Condition、Action、Situation 等）：
- Equipment: 涉及的设备/装置 (如反应釜、储罐、管道、泵、阀门)
- Material: 涉及的化学品/物料 (如丙烯腈、苯、氯气)
- Abnormal_Condition: 异常状态/事件 (如温度升高、压力超标、泄漏、违规操作)
- Consequence: 事故后果 (如爆炸、火灾、中毒、**人员伤亡**、财产损失)
- Mitigation: 应急/缓解措施 (如启动喷淋系统、紧急停车、疏散)

## 关系类型

必须且只能使用以下 3 种关系类型：
- leads_to: A 导致 B（因果关系）
- involves: A 涉及 B（设备或物料的参与关系）
- mitigated_by: 被某措施缓解

## 抽取规则

1. **因果顺序**：事件必须严格按照时间/因果先后排列。后果（Consequence）永远不能出现在原因之前。例如「先爆炸才死人」不能写成「人员伤亡 → 爆炸」。
2. **完整链条**：尽量抽取至少 3 步以上的连续因果链，避免拆成多个短对子。例如「泵故障 → 温度升高 → 自聚反应 → 压力飙升 → 爆炸」应整体输出，而不是拆成 4 条两两关系。
3. **伤亡概括化**：伤亡信息统一概括为「人员伤亡」「多人中毒」等通用表述，不要提取具体数字作为独立实体。
4. **忠实于原文**：只抽取报告明确提到的内容，不要补充原文没有的因果步骤。
5. **同一事故内部连贯**：同一台设备或物料在前文首次出现后用简称时，实体 name 保持一致。"""

    # ─── Few-shot 示例 ────────────────────────────────────────────────
    FEW_SHOT_EXAMPLE = """
## 示例

报告片段：
"2023年5月7日，某化工厂丙烯腈储罐区因冷却水循环泵故障，导致储罐温度持续上升。高温引发丙烯腈自聚放热反应，罐内压力急剧升高，最终储罐超压破裂，丙烯腈蒸气泄漏并遇静电火花发生爆炸。操作人员紧急启动泡沫灭火系统和罐区喷淋。"

正确输出：
{
  "event_chain": [
    {"entity": "冷却水循环泵", "type": "Equipment", "status": "故障"},
    {"relation": "leads_to", "target": "储罐温度持续上升"},
    {"entity": "储罐温度持续上升", "type": "Abnormal_Condition"},
    {"relation": "leads_to", "target": "丙烯腈自聚放热反应"},
    {"entity": "丙烯腈自聚放热反应", "type": "Abnormal_Condition"},
    {"relation": "leads_to", "target": "罐内压力急剧升高"},
    {"entity": "罐内压力急剧升高", "type": "Abnormal_Condition"},
    {"relation": "leads_to", "target": "储罐超压破裂"},
    {"entity": "储罐超压破裂", "type": "Abnormal_Condition"},
    {"relation": "leads_to", "target": "丙烯腈蒸气泄漏"},
    {"entity": "丙烯腈蒸气泄漏", "type": "Abnormal_Condition"},
    {"relation": "leads_to", "target": "遇静电火花发生爆炸"},
    {"entity": "遇静电火花发生爆炸", "type": "Consequence"},
    {"entity": "泡沫灭火系统和罐区喷淋", "type": "Mitigation", "action": "紧急启动"},
    {"relation": "mitigated_by", "target": "泡沫灭火系统和罐区喷淋"}
  ],
  "root_cause": "冷却水循环泵故障",
  "consequence": "丙烯腈储罐爆炸，丙烯腈蒸气泄漏"
}

注意这个示例中：
- 因果链从 Equipment 故障开始，经过 5 步 Abnormal_Condition，最终到达 Consequence，中间没有任何一步的跳跃
- 伤亡示例中使用了「遇静电火花发生爆炸」（Consequence），而非具体数字
- Mitigation 实体在链尾标注"""

    # ─── 抽取指令模板 ──────────────────────────────────────────────────
    EXTRACTION_TEMPLATE = """请分析以下事故报告片段，提取完整的因果事件链。

报告片段：
{report_text}

请严格遵守 System Prompt 中定义的 5 种实体类型和 3 种关系类型。
同时遵守以下规则：
1. 按实际因果顺序排列事件链，后果不能出现在原因前面
2. 尽量输出至少 3 步以上的连续因果链
3. 伤亡信息概括为「人员伤亡」「多人中毒」等通用表述，不输出具体数字
4. 只抽取报告中明确提到的内容，不补充缺失环节
5. entity 和 type 字段必须成对出现

输出 JSON 结构：
{{
  "event_chain": [
    {{"entity": "...", "type": "Equipment|Material|Abnormal_Condition|Consequence|Mitigation", "status": "..."}},
    {{"relation": "leads_to|involves|mitigated_by", "target": "..."}},
    ...
  ],
  "root_cause": "string（事故链起始故障的简述）",
  "consequence": "string（最终事故后果总结）"
}}"""

    # ─── 质量验证 Prompt ──────────────────────────────────────────────
    VALIDATION_PROMPT = """请验证以下抽取结果是否满足要求：
1. 所有实体类型是否属于预定义类型（Equipment, Material, Abnormal_Condition, Consequence, Mitigation）
2. 因果链是否连续完整
3. JSON 格式是否正确

抽取结果：
{extraction_result}

如有问题请指出具体问题，如没有问题请回复 "VALID"。"""

    @classmethod
    def format_extraction_prompt(cls, report_text: str) -> str:
        """格式化抽取 Prompt（含 Few-shot 示例）"""
        return cls.FEW_SHOT_EXAMPLE + "\n\n" + cls.EXTRACTION_TEMPLATE.format(report_text=report_text)

    @classmethod
    def get_system_prompt_with_rules(cls) -> str:
        """返回包含完整规则的 System Prompt"""
        return cls.SYSTEM_PROMPT
