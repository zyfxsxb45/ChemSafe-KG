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
- Equipment: 设备/装置。命名用技术全称(反应釜/冷却水循环泵/储罐/管道/阀门),不用简称
- Material: 化学品/物料。命名用标准名(丙烯腈/苯/氯气),不用俗名
- Abnormal_Condition: 异常状态/事件。命名用"主体+异常"模式(温度升高/压力超标/阀门失效/违规操作),≤15汉字
- Consequence: 事故后果(爆炸/火灾/中毒/人员伤亡)
- Mitigation: 应急措施。命名用"动作+对象"模式(启动喷淋/切断阀门/组织疏散),每项独立

关系类型(仅3种):
- leads_to: A导致B(因果)
- involves: A涉及B(设备与物料的参与关系,在链头使用)
- mitigated_by: 后果被措施缓解(紧接在Consequence之后)

规则:
1. 严格因果顺序,后果不在原因前
2. 至少3步连续因果链
3. 伤亡概括为"人员伤亡",不写具体数字
4. 只抽取原文明确内容
5. entity名≤15汉字,描述单一概念,不嵌入因果链
6. Equipment/Material优先识别,在链头用involves标注参与关系
7. 人员操作分离: 有具体设备时拆为Equipment→Abnormal_Condition; 无具体设备时只提取异常动作
8. Mitigation紧接Consequence之后放置; 扫描"防范措施/安全建议/教训"段落,每项措施独立"""

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
- 因果链从 Equipment 故障开始，经过 5 步 Abnormal_Condition，最终到 Consequence，无跳跃

人员操作分离示例：
报告"操作工误将甲醇阀门打开"的正确抽取：
  Equipment"甲醇阀门" → leads_to → Abnormal_Condition"误开阀门"
禁止写法：Abnormal_Condition"操作工误将甲醇阀门打开"（人员与设备合并）

常见错误对照：
  ✗ Mitigation"应急处置"（笼统合并）          → ✓ Mitigation"启动喷淋" + Mitigation"疏散人员"
  ✗ Abnormal"冷却水循环泵故障导致温度升高"（因果链嵌入） → ✓ Equipment"冷却水循环泵" → leads_to → Abnormal"温度升高"
  ✗ Equipment"泵"（简称,缺少上下文）          → ✓ Equipment"冷却水循环泵"
  ✗ 缺少Material节点,只在Abnormal中使用化学品名 → ✓ 链头用involves标注Material"""

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
6. ⚠️ 重要：仔细扫描文中的「防范措施」「安全建议」「教训」「整改要求」「应急处置」等段落，将每项具体措施作为独立的 Mitigation 实体抽取。Mitigation 紧接在它缓解的 Consequence 之后放置（如「…后果为爆炸。人员启动泡沫灭火系统…」→ Consequence"爆炸" → mitigated_by → Mitigation"启动泡沫灭火系统"）。不要合并为「应急处置」等笼统表述
7. ⚠️ 实体原子化：每个 entity 名称不得超过 15 个汉字，必须描述单一概念。禁止将因果链嵌入 entity 名中（如「泵故障导致温度升高」✗ → 应拆为 Equipment「泵」→ leads_to → Abnormal_Condition「温度升高」✓）
8. ⚠️ 人员操作分离：涉及操作人员的动作，先提取被操作的 Equipment，再提取 Abnormal_Condition 描述异常动作。禁止将人与动作合并为一个 entity（如「操作工误开阀门」✗ → Equipment「阀门」→ leads_to → Abnormal_Condition「误开阀门」✓）。无具体设备时只提取异常动作（如「违章作业」）
9. ⚠️ 设备物料优先：先识别所有 Equipment 和 Material 节点，再用 Abnormal_Condition 描述它们的异常行为。同一设备在链中复用必须保持 name 一致

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
