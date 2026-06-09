"""
ChemSafe-KG 期末汇报 PPT 生成脚本

生成完整的 25 页 PPTX，包含：
  - 封面 + 8个模块的内容页
  - 插入已生成的图表 PNG
  - 每页附讲稿备注
  - 统一样式（配色、字体、布局）

输出: ../期末汇报材料/ChemSafe-KG_期末汇报.pptx
"""
import os, sys, json
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)
sys.path.insert(0, '.')

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import pptx.oxml.ns as ns

# ═══ 全局设置 ═══════════════════════════════════════════════
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# 配色
C_BG       = RGBColor(0x0D, 0x1B, 0x2A)   # 深蓝黑背景
C_WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
C_ACCENT   = RGBColor(0x00, 0xB4, 0xD8)   # 青色
C_RED      = RGBColor(0xF4, 0x43, 0x36)
C_GREEN    = RGBColor(0x4C, 0xAF, 0x50)
C_ORANGE   = RGBColor(0xFF, 0x98, 0x00)
C_GREY     = RGBColor(0x90, 0xA4, 0xAE)
C_GREY_DK  = RGBColor(0x45, 0x55, 0x64)

CHART_DIR = Path('../期末汇报材料/charts')

# ═══ 工具函数 ═══════════════════════════════════════════════
def add_bg(slide):
    """设置幻灯片背景"""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = C_BG

def add_progress(slide, current, total):
    """左上角进度条"""
    left, top, w, h = Inches(0.5), Inches(0.25), Inches(12.3), Inches(0.04)
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = C_GREY_DK
    shape.line.fill.background()
    # 填充部分
    if current > 0:
        fill_w = int(w * current / total)
        shape2 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, fill_w, h)
        shape2.fill.solid()
        shape2.fill.fore_color.rgb = C_ACCENT
        shape2.line.fill.background()

def add_title(slide, text, y=Inches(0.6)):
    """添加页面标题"""
    txBox = slide.shapes.add_textbox(Inches(1), y, Inches(11.3), Inches(0.8))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = C_WHITE

def add_body(slide, text, left=Inches(1), top=Inches(1.8), width=Inches(11.3), height=Inches(5), size=Pt(20)):
    """添加正文"""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, line in enumerate(text.split('\n')):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = line
        p.font.size = size
        p.font.color.rgb = C_WHITE if not line.startswith('→') else C_GREY
        p.space_after = Pt(8)

def add_metric_card(slide, left, top, number, label, color=C_ACCENT):
    """添加度量卡片"""
    w, h = Inches(2.5), Inches(1.3)
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(0x1B, 0x2A, 0x3A)
    shape.line.color.rgb = C_GREY_DK
    shape.line.width = Pt(1)

    tf = shape.text_frame
    tf.word_wrap = True
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    p = tf.paragraphs[0]
    p.text = number
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = color

    p2 = tf.add_paragraph()
    p2.text = label
    p2.font.size = Pt(13)
    p2.font.color.rgb = C_GREY
    p2.alignment = PP_ALIGN.CENTER

def add_chart(slide, filename, left, top, width=None, height=None):
    """插入图表 PNG"""
    path = CHART_DIR / filename
    if not path.exists():
        add_body(slide, f"[图表 {filename} 缺失]", left, top, size=Pt(14))
        return
    w = width or Inches(5.5)
    h = height or Inches(4)
    slide.shapes.add_picture(str(path), left, top, w, h)

def add_notes(slide, text):
    """添加演讲者备注"""
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    tf.text = text

def add_section_header(slide, number, title, subtitle=""):
    """模块分隔页"""
    # 大数字
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(3), Inches(2))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = f"0{number}"
    p.font.size = Pt(96)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT
    # 标题
    txBox2 = slide.shapes.add_textbox(Inches(4.5), Inches(2.4), Inches(7.5), Inches(1.5))
    tf2 = txBox2.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = title
    p2.font.size = Pt(40)
    p2.font.bold = True
    p2.font.color.rgb = C_WHITE
    if subtitle:
        p3 = tf2.add_paragraph()
        p3.text = subtitle
        p3.font.size = Pt(18)
        p3.font.color.rgb = C_GREY

def new_slide():
    """创建空白幻灯片"""
    layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(layout)
    add_bg(slide)
    return slide


# ═══════════════════════════════════════════════════════════
#  P1: 封面
# ═══════════════════════════════════════════════════════════
slide = new_slide()
txBox = slide.shapes.add_textbox(Inches(1.5), Inches(1.8), Inches(10), Inches(2))
tf = txBox.text_frame
p = tf.paragraphs[0]
p.text = "ChemSafe-KG"
p.font.size = Pt(60)
p.font.bold = True
p.font.color.rgb = C_ACCENT
p2 = tf.add_paragraph()
p2.text = "基于大模型驱动的化工安全事故知识图谱"
p2.font.size = Pt(32)
p2.font.color.rgb = C_WHITE
p3 = tf.add_paragraph()
p3.text = "构建与因果推理问答系统"
p3.font.size = Pt(32)
p3.font.color.rgb = C_WHITE

txBox2 = slide.shapes.add_textbox(Inches(1.5), Inches(4.5), Inches(10), Inches(2))
tf2 = txBox2.text_frame
p = tf2.paragraphs[0]
p.text = "数据库技术及应用 · 期末汇报"
p.font.size = Pt(20)
p.font.color.rgb = C_GREY
p2 = tf2.add_paragraph()
p2.text = "翟彝凡  余亮阳  赵乐毅  |  指导老师：王健楠 教授"
p2.font.size = Pt(16)
p2.font.color.rgb = C_GREY
p3 = tf2.add_paragraph()
p3.text = "2026年6月"
p3.font.size = Pt(16)
p3.font.color.rgb = C_GREY
add_notes(slide, "开场：大家好，我们组做的是ChemSafe-KG...")

# ═══════════════════════════════════════════════════════════
#  P2: 研究动机
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 1, 25)
add_title(slide, "研究动机")
add_body(slide, "化工安全事故\"小概率、大后果\"——单起事故可致上百人伤亡、数亿元损失\n\n事故调查报告分散在政府网站、行业数据库中，以非结构化文本存在\n\n传统分析方法依赖人工阅读，难以系统查询和模式归纳\n\n大模型有幻觉——编造不存在的事故原因，在安全领域是致命缺陷\n\n→ 核心动机：用LLM自动构建知识图谱，再用图谱约束LLM，控制幻觉",
         top=Inches(1.6))
add_metric_card(slide, Inches(1), Inches(5.5), "1,579", "事故记录", C_RED)
add_metric_card(slide, Inches(4), Inches(5.5), "6,976", "KG节点", C_ACCENT)
add_metric_card(slide, Inches(7), Inches(5.5), "23,111", "关系边", C_GREEN)
add_metric_card(slide, Inches(10), Inches(5.5), "79年", "时间跨度", C_ORANGE)

add_notes(slide, """模块一：研究动机
化工安全事故"小概率大后果"。事故报告碎片化。大模型有幻觉。能否用LLM构建KG，再用KG约束LLM？""")

# ═══════════════════════════════════════════════════════════
#  P3: 核心问题与挑战
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 2, 25)
add_title(slide, "核心问题与挑战")
add_body(slide, """问题一：自动化KG构建
  从1,300+份非结构化中文事故报告中，自动抽取实体与因果关系
  中文事故文本长句多、实体边界模糊

问题二：因果约束问答
  纯LLM回答安全问题时平均每题产生6个幻觉实体
  需要因果路径约束生成空间，每条陈述标注来源

问题三：多源数据融合
  事故报告 + 微信公众号 + 化学品物性 + 气象数据
  格式各异，需统一分析视图""",
         top=Inches(1.6), size=Pt(18))
add_notes(slide, "三个具体挑战：自动化构建、因果约束、多源融合。数据规模引出。")

# ═══════════════════════════════════════════════════════════
#  P4: 分隔页 — 解决方法
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_section_header(slide, 1, "解决方法", "五层架构 · Prompt Chain · Graph RAG")
add_notes(slide, "接下来由余亮阳介绍技术方案")

# ═══════════════════════════════════════════════════════════
#  P5: 系统架构
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 5, 25)
add_title(slide, "系统架构：五层设计")
add_chart(slide, '08_architecture.png', Inches(1), Inches(1.5), Inches(11.3), Inches(5.5))
add_notes(slide, "五层架构。从下往上：数据获取层、LLM抽取层、知识存储层、GraphRAG检索层、Streamlit应用层。")

# ═══════════════════════════════════════════════════════════
#  P6: Prompt Chain 知识抽取
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 6, 25)
add_title(slide, "LLM知识抽取：Prompt Chain 策略")
add_body(slide, """核心设计：5种实体类型 × 3种关系类型 + Few-shot示例 + 8条精炼规则

实体类型：Equipment（设备） | Material（物料） | Abnormal_Condition（异常状态）
         Consequence（后果） | Mitigation（应急措施）
关系类型：leads_to（因果） | involves（参与） | mitigated_by（缓解）

关键规则（经过数十条失败案例迭代）：
  规则5 — entity名≤15汉字，描述单一概念
  规则7 — 人员操作分离：\"操作工误开阀门\"拆为 Equipment+Abnormal_Condition
  规则8 — Mitigation紧接Consequence，每项措施独立，不合并

JSON三级容错：空响应→自动修复→正则提取 → 抽取成功率99%+""",
         top=Inches(1.4), size=Pt(16))
add_notes(slide, "Prompt Chain是核心创新之一。5实体×3关系+8条规则。特别注意规则5和7——事件原子化和人员操作分离。JSON三级容错保证鲁棒性。")

# ═══════════════════════════════════════════════════════════
#  P7: 三层实体匹配
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 7, 25)
add_title(slide, "问答检索：三层实体匹配 + 融合加权")
add_body(slide, """L1 — 精确匹配：用户问题中的实体名与KG节点名精确/包含匹配，置信度0.6-1.0

L2 — 关键词命中：jieba分词提取关键词，与KG实体名交叉对比，命中数加权

L3 — 嵌入语义匹配：sentence-transformers（paraphrase-multilingual-MiniLM-L12-v2）
    实体名清洗（提取设备/化学品/状态关键词）+ 自适应阈值 + 泛化词过滤
    解决\"液氯→氯气\"\"反应釜→聚合釜\"等同义匹配问题

统一融合：score = L1置信度×3 + L2命中数×1 + L3相似度×3 + 有因果路径的奖励×2""",
         top=Inches(1.6), size=Pt(16))
add_notes(slide, "三层匹配策略。关键是嵌入语义层解决同义词匹配，融合加权公式有实验依据。")

# ═══════════════════════════════════════════════════════════
#  P8: Graph RAG 约束问答
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 8, 25)
add_title(slide, "Graph RAG：因果路径约束的答案生成")
add_body(slide, """检索阶段：匹配实体 → Cypher查询因果路径（最大深度3-4）→ 去重与子路径过滤

约束系统Prompt（核心）：
  1. 严格按照检索到的因果路径中的事实回答，不得添加推测
  2. 如果路径与问题无关或为空，直接回答\"根据当前知识图谱，无法回答该问题\"
  3. 每条关键陈述末尾标注来源路径编号，格式为 [路径N]
  4. 按因果时间顺序组织回答：事故链条概述 → 关键节点解释 → 安全建议

→ Graph RAG不是让答案\"更好\"，而是让答案\"更可信\"——每条陈述可追溯""",
         top=Inches(1.6), size=Pt(16))
add_notes(slide, "GraphRAG的核心价值不是回答得更好，而是回答得更可信——每条陈述可以追溯到具体来源。诚实拒答是安全领域的刚需。")

# ═══════════════════════════════════════════════════════════
#  P9: 双存储架构
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 9, 25)
add_title(slide, "双存储：Neo4j + SQLite 跨源链接")
add_body(slide, """Neo4j 5.26（图数据库）               SQLite（关系数据库）
  ├─ 因果链存储与路径查询              ├─ 结构化事故记录(1,579条)
  ├─ 6,976节点 / 23,111关系边          ├─ 化学品物性(29种)
  ├─ Accident聚合节点(1,579个)          ├─ 4索引 + 1分析视图
  ├─ 5类节点索引 + UNIQUE约束          ├─ SQL分析查询
  └─ belongs_to 归组                    └─ Pandas数据融合

跨源链接器(DataLinker)：
  • 化学品物性 → Material节点属性同步
  • 双存储一致性校验（覆盖率 + 孤立节点检测）
  • 图密度=0.0005，平均度=3.3""",
         top=Inches(1.4), size=Pt(15))
add_notes(slide, "双存储设计：图数据库做因果链，关系数据库做统计分析。跨源链接器做双向同步。Accident节点是v0.7新功能。")

# ═══════════════════════════════════════════════════════════
#  P10: 多源数据
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 10, 25)
add_title(slide, "多源数据采集")
add_body(slide, """mem.gov.cn 应急管理部         微信公众号                     PubChem
  95个月度汇编页全量采集         74篇事故分析文章               29种危化品物性
  1,261份事故报告                含安全建议/教训反思            100%含CAS/IUPAC
  BeautifulSoup解析              108篇筛选→74篇保存             分子量/闪点/爆炸极限

数据处理流水线：
  爬虫(mem) + JSON预处理(微信) → 文本清洗(噪声去除+PII脱敏+智能分段)
  → 多源融合(事故↔化学品 + 事故↔气象) → 统一分析视图(1,813行×19列)""",
         top=Inches(1.5), size=Pt(16))
add_notes(slide, "三个数据源。微信文章是Mitigation节点的主要来源。mem月度汇编是一事一报的简短摘要。")

# ═══════════════════════════════════════════════════════════
#  P11: 分隔页 — 实验评测
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_section_header(slide, 2, "实验评测", "数据规模 · 对照实验 · 洞察发现")
add_notes(slide, "接下来由赵乐毅介绍实验评测")

# ═══════════════════════════════════════════════════════════
#  P12: 数据规模
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 12, 25)
add_title(slide, "最终数据规模")
add_chart(slide, '05_node_types.png', Inches(0.5), Inches(1.5), Inches(6), Inches(5.5))
# 右侧文字
add_body(slide, """6,976 节点 | 23,111 关系 | 1,579 事故

Mitigation: 4 → 71（9x 提升）
Accident: 0 → 1,579（v0.7新功能）

节点分布：
  Abnormal_Condition 3,570 (51%)
  Accident 1,579 (23%)
  Equipment 688 (10%)
  Consequence 641 (9%)
  Material 427 (6%)
  Mitigation 71 (1%)""",
         left=Inches(7), top=Inches(1.8), size=Pt(15))
add_notes(slide, "最终数据规模。Mitigation从4到71是Prompt改进+微信数据的结果。Abnormal占比51%是事件原子化的直接效果。")

# ═══════════════════════════════════════════════════════════
#  P13: 对照实验设计
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 13, 25)
add_title(slide, "对照实验设计：三组Baseline")
add_body(slide, """实验目标：用数据回答\"知识图谱到底有没有必要？\"

Baseline 1 — 关键词RAG       Baseline 2 — Graph RAG        Baseline 3 — 纯LLM
  jieba分词 + SQLite检索        KG因果路径约束LLM              无任何数据约束
  Top8文本 → LLM回答            三层匹配 → 路径检索             凭参数化知识回答
                                  → 约束生成+来源引用

20道测试题 × 7种因果模式（因果链查询/致因归纳/边界测试/泛化/设备后果/化学品/措施）
每道题预设标准答案节点（预期因果链关键节点列表）

四维评估：无幻觉率 | 来源可追溯率 | 节点命中率 | 诚实拒答率""",
         top=Inches(1.4), size=Pt(16))
add_notes(slide, "实验设计回应老师期中提出的KG必要性问题。三组对比覆盖了纯LLM、文本检索、KG检索三个层次。")

# ═══════════════════════════════════════════════════════════
#  P14: 实验结果
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 14, 25)
add_title(slide, "实验结果：Graph RAG 减少9倍幻觉")
add_chart(slide, '07_experiment.png', Inches(0.5), Inches(1.5), Inches(12.3), Inches(5))
add_notes(slide, """核心页。重点讲解：
1. 无幻觉率70% vs 5%：9倍差距
2. 平均幻觉数0.65 vs 5.95：纯LLM每题编6个实体
3. 诚实拒答55% vs 0%：纯LLM从不拒答，在安全领域致命
4. 节点命中率低是因为标准答案包含KG不一定有的精确节点，是参考性指标""")

# ═══════════════════════════════════════════════════════════
#  P15: 事故类型与时间
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 15, 25)
add_title(slide, "数据洞察：事故类型与时间趋势")
add_chart(slide, '01_accident_types.png', Inches(0.3), Inches(1.5), Inches(6.2), Inches(5))
add_chart(slide, '02_timeline.png', Inches(6.8), Inches(1.5), Inches(6.2), Inches(5))
add_notes(slide, "事故类型：爆炸61%+中毒27%=88%。时间趋势：2010s高峰，2020s下降。")

# ═══════════════════════════════════════════════════════════
#  P16: 化学品与设备
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 16, 25)
add_title(slide, "数据洞察：化学品与设备频次")
add_chart(slide, '03_chemicals.png', Inches(0.3), Inches(1.5), Inches(6.2), Inches(5))
add_chart(slide, '04_equipment.png', Inches(6.8), Inches(1.5), Inches(6.2), Inches(5))
add_notes(slide, "硫化氢49起排第一。氮气43起——本身无毒但是窒息事故主因。反应釜62起遥遥领先——高温高压工艺条件。")

# ═══════════════════════════════════════════════════════════
#  P17: 最危险状态
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 17, 25)
add_title(slide, "数据洞察：最危险中间异常状态")
add_chart(slide, '06_dangerous_states.png', Inches(1), Inches(1.5), Inches(11), Inches(5.5))
add_notes(slide, "形成爆炸性混合气体关联102个后果节点，是事故链中最关键的薄弱环节。前8名中有5个与可燃气体/爆炸相关。")

# ═══════════════════════════════════════════════════════════
#  P18: 分隔页 — 系统演示
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_section_header(slide, 3, "系统演示", "Streamlit Web应用 · 因果推理问答 · 可视化")
add_notes(slide, "接下来由翟彝凡演示系统")

# ═══════════════════════════════════════════════════════════
#  P19: 问答演示
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 19, 25)
add_title(slide, "演示：因果推理问答")
add_body(slide, """输入："反应釜温度失控如何导致爆炸？"

系统流程：
  ① 三层匹配在KG中定位相关实体（反应釜、温度升高、压力超标…）
  ② Cypher查询因果路径 → 检索到4条因果链
  ③ Graph RAG约束生成 → 因果链概述 + 关键节点解释 + 安全建议
  ④ 每条陈述标注来源：\"温度升高引发反应加速[路径1]\"

→ 在Web应用中实时演示""",
         top=Inches(1.6), size=Pt(20))
add_body(slide, "[现场操作录屏或截图演示]", left=Inches(1), top=Inches(5.5), size=Pt(16))
add_notes(slide, "现场演示问答流程。提前准备一个确凿能在KG中找到的案例——推荐'反应釜温度失控'或'有限空间作业中毒窒息'。")

# ═══════════════════════════════════════════════════════════
#  P20: 可视化演示
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 20, 25)
add_title(slide, "演示：因果路径可视化与数据仪表盘")
add_body(slide, """因果路径有向图              数据仪表盘
  Equipment → Abnormal           6种图表实时切换
    → Consequence                • 事故趋势柱状图
    → Mitigation                 • 化学品频次柱状图
  每类节点不同颜色/形状           • 设备频次统计
  (截图演示)                     • 类型饼图
                                  • 图谱桑基图
                                  (截图演示)""",
         top=Inches(1.6), size=Pt(18))
add_notes(slide, "因果路径有向图展示完整因果链。数据仪表盘可切换6种视图。")

# ═══════════════════════════════════════════════════════════
#  P21: 分隔页 — 收获与展望
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_section_header(slide, 4, "收获与展望", "技术心得 · 未来方向")
add_notes(slide, "收获与展望，赵乐毅和余亮阳")

# ═══════════════════════════════════════════════════════════
#  P22: 收获感悟
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 22, 25)
add_title(slide, "收获与感悟")
add_body(slide, """1. Prompt工程是一门精细的迭代科学
   最早只有6条规则，抽取的实体名像\"操作人员未佩戴防护用品情况下盲目进入有限空间施救\"
   逐步加规则（事件原子化、人员分离、反例）→ 每条规则背后是数十条失败案例分析

2. 双存储架构不是过度设计
   图数据库表达因果\"A导致B\"——天然有向边
   关系数据库做统计查询——SQL远比Cypher直观
   各司其职，跨源链接双向同步

3. \"用LLM建KG，再用KG约束LLM\"这个闭环有实验证据支撑
   对照实验给出了量化答案：幻觉减少9倍，边界外诚实拒答
   这个结论不是我们说的，是数据说的""",
         top=Inches(1.2), size=Pt(16))
add_notes(slide, "三个核心收获。强调每条规则背后的迭代——不是一次写对的。")

# ═══════════════════════════════════════════════════════════
#  P23: 未来工作
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 23, 25)
add_title(slide, "未来工作")
add_body(slide, """数据源扩展：CSB英文调查报告（含完整安全建议章节）+ ciedu.com.cn完整事故报告
           → 显著提升Mitigation节点数量和因果链深度

多语言支持：接入eMARS欧盟事故数据库 + 英文文献，实现跨语言事故模式对比

实体消歧：\"形成爆炸性混合气体\"与\"形成爆炸性混合物\"自动合并
         → 提升图谱连通性和查询覆盖

风险预测：从\"回溯分析\"走向\"事前预防\"
         基于历史数据训练模型，预测设备故障概率和事故风险""",
         top=Inches(1.5), size=Pt(17))
add_notes(slide, "四个未来方向。CSB数据是首要的——调查报告质量最高，含有完整安全建议。")

# ═══════════════════════════════════════════════════════════
#  P24: 项目总结
# ═══════════════════════════════════════════════════════════
slide = new_slide()
add_progress(slide, 24, 25)
add_title(slide, "项目总结")
add_body(slide, """ChemSafe-KG：首个大规模中文化工安全事故知识图谱

  • 1,579起事故 × 6,976节点 × 23,111关系边，1947-2026
  • Neo4j图数据库 + SQLite关系数据库，双存储 + 跨源链接
  • LLM驱动的Prompt Chain策略，99%+抽取成功率，JSON三级容错
  • 三层实体匹配 + Graph RAG约束问答，每条陈述标注来源路径

实验核心结论：Graph RAG比纯LLM减少9倍幻觉（0.65 vs 5.95）
              诚实拒答率55%（纯LLM为0%）

数据集以CC BY-NC许可公开发布于GitHub""",
         top=Inches(1.2), size=Pt(17))
add_notes(slide, "总结。四个核心数字+实验结论+数据集开源。")

# ═══════════════════════════════════════════════════════════
#  P25: 感谢 & Q&A
# ═══════════════════════════════════════════════════════════
slide = new_slide()
txBox = slide.shapes.add_textbox(Inches(1.5), Inches(2.5), Inches(10), Inches(3))
tf = txBox.text_frame
p = tf.paragraphs[0]
p.text = "感谢聆听"
p.font.size = Pt(56)
p.font.bold = True
p.font.color.rgb = C_ACCENT
p.alignment = PP_ALIGN.CENTER

p2 = tf.add_paragraph()
p2.text = "欢迎提问 & 交流讨论"
p2.font.size = Pt(24)
p2.font.color.rgb = C_GREY
p2.alignment = PP_ALIGN.CENTER

p3 = tf.add_paragraph()
p3.text = ""
p3.font.size = Pt(14)

p4 = tf.add_paragraph()
p4.text = "GitHub: [repository] | 数据集: CC BY-NC 4.0"
p4.font.size = Pt(14)
p4.font.color.rgb = C_GREY_DK
p4.alignment = PP_ALIGN.CENTER

add_notes(slide, "感谢王老师的指导，感谢各位同学。我们接受提问。")


# ═══════════════════════════════════════════════════════════
#  保存
# ═══════════════════════════════════════════════════════════
OUT_PATH = '../期末汇报材料/ChemSafe-KG_期末汇报.pptx'
prs.save(OUT_PATH)
print(f"PPT saved: {OUT_PATH}")
print(f"Slides: {len(prs.slides)}")
