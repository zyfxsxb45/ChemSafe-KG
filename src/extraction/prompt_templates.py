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
    SYSTEM_PROMPT = """你是化工安全专家。从事故报告中提取因果事件链。

实体类型(仅5种):
- Equipment: 设备(反应釜/储罐/管道/泵/阀门)
- Material: 物料(丙烯腈/苯/氯气)
- Abnormal_Condition: 异常(温度升高/压力超标/泄漏/违规操作)
- Consequence: 后果(爆炸/火灾/中毒/人员伤亡)
- Mitigation: 措施(启动喷淋/紧急停车/疏散/检测/佩戴/隔离/培训/整改)

关系类型(仅3种):
- leads_to: A导致B
- involves: A涉及B
- mitigated_by: 被措施缓解

规则:
1. 严格因果顺序,后果不在原因前
2. 至少3步连续因果链
3. 伤亡概括为"人员伤亡",不写具体数字
4. 只抽取原文明确内容
5. entity名≤15汉字,描述单一概念,不嵌入因果链(如写"温度升高"不写"泵故障导致温度升高")
6. Equipment/Material优先识别,再用Abnormal_Condition描述其异常
7. 扫描"防范措施/安全建议/应急处置/教训"段落,每项措施独立为Mitigation,不合并为笼统表述"""

    # ─── Few-shot 示例 ────────────────────────────────────────────────
    FEW_SHOT_EXAMPLE = """
## 示例

报告片段：
"2023年5月7日，某化工厂丙烯腈储罐区因冷却水循环泵故障，导致储罐温度持续上升。高温引发丙烯腈自聚放热反应，罐内压力急剧升高，最终储罐超压破裂，丙烯腈蒸气泄漏并遇静电火花发生爆炸。操作人员紧急启动泡沫灭火系统和罐区喷淋。"

正确输出：
{
  "event_chain": [
    {"entity": "冷却水循环泵", "type": "Equipment", "status": "故障"},
    {"relation": "involves", "target": "丙烯腈"},
    {"entity": "丙烯腈", "type": "Material"},
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
    {"entity": "泡沫灭火系统", "type": "Mitigation", "action": "紧急启动"},
    {"relation": "mitigated_by", "target": "泡沫灭火系统"},
    {"entity": "罐区喷淋", "type": "Mitigation", "action": "紧急启动"},
    {"relation": "mitigated_by", "target": "罐区喷淋"},
    {"entity": "人员疏散至安全区域", "type": "Mitigation", "action": "组织"},
    {"relation": "mitigated_by", "target": "人员疏散至安全区域"},
    {"entity": "切断进料阀门", "type": "Mitigation", "action": "紧急"},
    {"relation": "mitigated_by", "target": "切断进料阀门"}
  ],
  "root_cause": "冷却水循环泵故障",
  "consequence": "丙烯腈储罐爆炸，丙烯腈蒸气泄漏"
}

注意这个示例中：
- Equipment「冷却水循环泵」→ involves → Material「丙烯腈」：设备与物料的参与关系在链头独立标注
- Material「丙烯腈」在首次出现时独立抽取，后续 Abnormal_Condition 中可引用
- 每一项 Mitigation 独立成实体（「泡沫灭火系统」与「罐区喷淋」分开），不合并
- Entity 名均不超过 15 个汉字，且每个 entity 只描述单一事实
- 因果链从 Equipment 故障开始，经过 5 步 Abnormal_Condition，最终到 Consequence，无跳跃"""

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
6. ⚠️ 重要：仔细扫描文中的「防范措施」「安全建议」「教训」「整改要求」「应急处置」等段落，将每项具体措施作为独立的 Mitigation 实体抽取（如「佩戴空气呼吸器」「气体检测合格后方可进入」「切断进料」），不要合并为「应急处置」等笼统表述
7. ⚠️ 实体原子化：每个 entity 名称不得超过 15 个汉字，必须描述单一概念。禁止将因果链嵌入 entity 名中（如「泵故障导致温度升高」✗ → 应拆为 Equipment「泵」→ leads_to → Abnormal_Condition「温度升高」✓）
8. ⚠️ 设备物料优先：先识别所有 Equipment 和 Material 节点，再用 Abnormal_Condition 描述它们的异常行为。同一设备在链中复用必须保持 name 一致

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
