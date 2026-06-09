"""
ChemSafe-KG 期末汇报 PPT 生成脚本 v2

改进：
  - 26 页，v2 讲稿对应
  - 左上角导航点（8个模块标记）
  - 更好的视觉层次和信息密度
  - 分隔页不再显示进度

输出: ../期末汇报材料/ChemSafe-KG_期末汇报.pptx
"""
import os, sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)
sys.path.insert(0, '.')

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

C_BG      = RGBColor(0x0D, 0x1B, 0x2A)
C_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
C_ACCENT  = RGBColor(0x00, 0xB4, 0xD8)
C_RED     = RGBColor(0xF4, 0x43, 0x36)
C_GREEN   = RGBColor(0x4C, 0xAF, 0x50)
C_ORANGE  = RGBColor(0xFF, 0x98, 0x00)
C_GREY    = RGBColor(0x90, 0xA4, 0xAE)
C_GREY_DK = RGBColor(0x45, 0x55, 0x64)

CHART_DIR = Path('D:/课程文件/大二下/数据库技术及应用/大作业/期末汇报材料/charts')


# ═══ Helpers ═══════════════════════════════════════════════
def add_bg(slide):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = C_BG

def add_dots(slide, section, total_sections=5):
    """左上角导航点：实心=当前section之前，空心=之后"""
    left, top = Inches(0.4), Inches(0.2)
    for i in range(total_sections):
        x = left + Inches(i * 0.32)
        dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, x, top, Inches(0.2), Inches(0.2))
        dot.fill.solid()
        if i < section:
            dot.fill.fore_color.rgb = C_ACCENT
        else:
            dot.fill.fore_color.rgb = C_GREY_DK
        dot.line.fill.background()
    # section label
    labels = ['', '问题', '方法', '实验', '演示', '总结']
    if section < len(labels) and labels[section]:
        tb = slide.shapes.add_textbox(left + Inches(total_sections * 0.32 + 0.15), Inches(0.16), Inches(2), Inches(0.3))
        tb.text_frame.paragraphs[0].text = labels[section]
        tb.text_frame.paragraphs[0].font.size = Pt(10)
        tb.text_frame.paragraphs[0].font.color.rgb = C_GREY

def add_title(slide, text, y=Inches(0.6)):
    txBox = slide.shapes.add_textbox(Inches(1), y, Inches(11.3), Inches(0.8))
    tf = txBox.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = text
    p.font.size = Pt(32); p.font.bold = True; p.font.color.rgb = C_WHITE

def add_body(slide, text, left=Inches(1), top=Inches(1.8), width=Inches(11.3), height=Inches(5), size=Pt(18)):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame; tf.word_wrap = True
    for i, line in enumerate(text.split('\n')):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = size if not line.startswith('  ') else Pt(size.pt - 2)
        p.font.color.rgb = C_WHITE if not line.startswith('→') else C_GREY
        p.space_after = Pt(6)

def add_metric(slide, left, top, num, label, color=C_ACCENT):
    w, h = Inches(2.6), Inches(1.3)
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, w, h)
    shape.fill.solid(); shape.fill.fore_color.rgb = RGBColor(0x1B, 0x2A, 0x3A)
    shape.line.color.rgb = C_GREY_DK; shape.line.width = Pt(1)
    tf = shape.text_frame; tf.word_wrap = True
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    p = tf.paragraphs[0]; p.text = num; p.font.size = Pt(36); p.font.bold = True; p.font.color.rgb = color
    p2 = tf.add_paragraph(); p2.text = label; p2.font.size = Pt(13); p2.font.color.rgb = C_GREY
    p2.alignment = PP_ALIGN.CENTER

def add_chart(slide, filename, left, top, width=None, height=None):
    path = CHART_DIR / filename
    if path.exists():
        slide.shapes.add_picture(str(path), left, top, width or Inches(5.5), height or Inches(4))

def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text

def add_section(slide, num, title, subtitle=""):
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(3), Inches(2))
    p = txBox.text_frame.paragraphs[0]; p.text = f"0{num}"; p.font.size = Pt(96); p.font.bold = True; p.font.color.rgb = C_ACCENT
    txBox2 = slide.shapes.add_textbox(Inches(4.5), Inches(2.4), Inches(7.5), Inches(1.5))
    tf2 = txBox2.text_frame
    p2 = tf2.paragraphs[0]; p2.text = title; p2.font.size = Pt(40); p2.font.bold = True; p2.font.color.rgb = C_WHITE
    if subtitle:
        p3 = tf2.add_paragraph(); p3.text = subtitle; p3.font.size = Pt(18); p3.font.color.rgb = C_GREY

def add_highlight(slide, left, top, width, height, text, color=C_ACCENT):
    """强调框"""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid(); shape.fill.fore_color.rgb = RGBColor(0x00, 0x7A, 0x8C)
    shape.line.fill.background()
    tf = shape.text_frame; tf.word_wrap = True
    tf.paragraphs[0].text = text; tf.paragraphs[0].font.size = Pt(16); tf.paragraphs[0].font.color.rgb = C_WHITE
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER

def new_slide(with_dots=True, section=0):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide)
    if with_dots:
        add_dots(slide, section)
    return slide


# ═══════════════════════════════════════════════════════════
#  P1: 封面
# ═══════════════════════════════════════════════════════════
slide = new_slide(with_dots=False)
txBox = slide.shapes.add_textbox(Inches(1.5), Inches(1.8), Inches(10), Inches(2.5))
tf = txBox.text_frame
p = tf.paragraphs[0]; p.text = "ChemSafe-KG"; p.font.size = Pt(64); p.font.bold = True; p.font.color.rgb = C_ACCENT
p2 = tf.add_paragraph(); p2.text = "基于大模型驱动的化工安全事故知识图谱"; p2.font.size = Pt(28); p2.font.color.rgb = C_WHITE
p3 = tf.add_paragraph(); p3.text = "构建与因果推理问答系统"; p3.font.size = Pt(28); p3.font.color.rgb = C_WHITE

txBox2 = slide.shapes.add_textbox(Inches(1.5), Inches(4.8), Inches(10), Inches(2))
tf2 = txBox2.text_frame
p = tf2.paragraphs[0]; p.text = "数据库技术及应用 · 期末汇报"; p.font.size = Pt(18); p.font.color.rgb = C_GREY
p2 = tf2.add_paragraph(); p2.text = "翟彝凡  余亮阳  赵乐毅  |  王健楠 教授"; p2.font.size = Pt(16); p2.font.color.rgb = C_GREY
p3 = tf2.add_paragraph(); p3.text = "2026年6月"; p3.font.size = Pt(16); p3.font.color.rgb = C_GREY
add_notes(slide, "开场：大家好，我们组做的是ChemSafe-KG...")

# ═══════════════════════════════════════════════════════════
#  P2: 研究动机
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=1)
add_title(slide, "研究动机")
add_body(slide, """化工安全"小概率、大后果" —— 单起事故可致上百人伤亡

事故报告分散 —— 碎片化的非结构化文本，难以系统查询和模式归纳

大模型有幻觉 —— 在安全领域，一个编造的答案比没有答案更危险

→ 核心动机：用LLM自动构建知识图谱，再用图谱约束LLM，控制幻觉，让回答可信""",
         top=Inches(1.6), size=Pt(20))
add_metric(slide, Inches(0.8), Inches(5.5), "1,579", "事故记录", C_RED)
add_metric(slide, Inches(3.7), Inches(5.5), "6,976", "KG 节点", C_ACCENT)
add_metric(slide, Inches(6.6), Inches(5.5), "23,111", "关系边", C_GREEN)
add_metric(slide, Inches(9.5), Inches(5.5), "79年", "时间跨度", C_ORANGE)
add_notes(slide, "天津港爆炸165人遇难。报告三百页。一线安全员需要的是问答式的知识网络。大模型有幻觉——在安全领域致命。")

# ═══════════════════════════════════════════════════════════
#  P3: 核心问题
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=1)
add_title(slide, "三个核心问题")
add_body(slide, """① 自动化KG构建
   从1,300+份中文化工事故报告中自动抽取实体与因果关系
   长句多、术语密、实体边界模糊 → Prompt Chain策略

② 因果约束问答
   控制大模型幻觉，让每条陈述有据可查
   对照实验：纯LLM平均每题编造6个不在图谱中的实体

③ 多源数据融合
   事故报告（mem.gov.cn）+ 微信公众号 + 化学品物性（PubChem）
   格式各异，需统一为可查询的分析视图""",
         top=Inches(1.6), size=Pt(19))
add_notes(slide, "三个问题。每个附带一个量化指标——增强说服力。")

# ═══════════════════════════════════════════════════════════
#  P4: 分隔页
# ═══════════════════════════════════════════════════════════
slide = new_slide(with_dots=False)
add_section(slide, 1, "解决方法", "五层架构 · Prompt Chain · Graph RAG")
add_notes(slide, "余亮阳：技术方案")

# ═══════════════════════════════════════════════════════════
#  P5: 架构
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=2)
add_title(slide, "系统架构：五层 · 单向数据流")
add_chart(slide, '08_architecture.png', Inches(0.8), Inches(1.5), Inches(11.5), Inches(5.5))
add_notes(slide, "五层架构。采→抽→存→检→答。每层接口清晰。")

# ═══════════════════════════════════════════════════════════
#  P6: Prompt Chain
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=2)
add_title(slide, "LLM知识抽取：Prompt Chain 策略")
# Left: rules
add_body(slide, """核心设计：5实体类型 × 3关系类型 + Few-shot示例 + 8条迭代规则

关键规则（经过数十条失败案例迭代）：
  规则5 — entity名 ≤15汉字，单一概念
  规则7 — "操作工误开阀门" → Equipment"阀门" + Abnormal"误开阀门"
  规则8 — 每项Mitigation独立，紧接Consequence之后

Few-shot示例 → 模型明确期望格式
JSON三级容错 → 空响应重试 / 自动修复 / 正则提取 → 99%+成功率""",
         left=Inches(0.8), top=Inches(1.4), width=Inches(6), size=Pt(15))
# Right: highlight box
add_highlight(slide, Inches(7.2), Inches(2.5), Inches(5.3), Inches(3.5),
    "Few-shot 示例\n\n冷却水循环泵(Equipment)\n  → involves → 丙烯腈(Material)\n  → leads_to → 温度升高(Abnormal)\n  → leads_to → 自聚放热(Abnormal)\n  → leads_to → 爆炸(Consequence)\n  → mitigated_by → 泡沫灭火(Mitigation)")
add_notes(slide, "Prompt迭代十几版。每条规则的名字你知道它要解决什么问题。Few-shot是最有力的格式约束。")

# ═══════════════════════════════════════════════════════════
#  P7: 三层匹配
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=2)
add_title(slide, "问答检索：三层实体匹配 + 融合加权")
add_body(slide, """L1 精确匹配 — 分词后直接比对KG节点名，置信度 0.6-1.0

L2 关键词命中 — jieba分词，与实体名交叉对比，命中数加权

L3 嵌入语义 — sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
    实体名清洗 + 自适应阈值 + 泛化词过滤
    "液氯"→"氯气"  "反应釜"→"聚合釜"

统一融合：score = L1×3 + L2×1 + L3×3 + 有路径奖励×2""",
         top=Inches(1.6), size=Pt(18))
add_notes(slide, "三层匹配并行。核心是L3嵌入语义——解决同义词。融合权重有实验调优。路径奖励鼓励图中有出边的实体。")

# ═══════════════════════════════════════════════════════════
#  P8: Graph RAG
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=2)
add_title(slide, "Graph RAG：因果路径约束生成")
add_body(slide, """检索 → 三层匹配定位实体 → Cypher查询因果路径（max depth 3-4）
      → 去重 + 子路径过滤 → 格式化上下文

约束系统Prompt（核心约束）：
  ✓ 严格按检索路径回答，不得添加推测
  ✓ 路径为空或无关时 → "根据当前知识图谱，无法回答该问题"
  ✓ 每条关键陈述标注来源[路径N]

→ 不是让答案"更好"，而是让答案"更可信" —— 每条陈述可追溯""",
         top=Inches(1.4), size=Pt(17))
add_notes(slide, "GraphRAG核心。三条硬约束。诚实拒答在安全领域是刚需。来源标注让答案可追溯。")

# ═══════════════════════════════════════════════════════════
#  P9: 双存储
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=2)
add_title(slide, "双存储：Neo4j + SQLite")
add_body(slide, """Neo4j 5.26（图）                    SQLite（关系）
  ├ 因果链存储 & 路径查询              ├ 事故记录 (1,579条)
  ├ 6,976 节点 | 23,111 边             ├ 化学品物性 (29种)
  ├ Accident 聚合 (1,579)              ├ SQL 分析 + 聚合查询
  └ belongs_to 归组                    └ Pandas 数据融合

设计哲学：图数据库做因果链——"A导致B"是天然有向边
          关系数据库做统计——GROUP BY比Cypher直观高效
          不是过度设计，是各司其职""",
         top=Inches(1.4), size=Pt(17))
add_notes(slide, "双存储不是过度设计。两种数据库解决的问题类型确实不同。Accident节点是v0.7新功能。")

# ═══════════════════════════════════════════════════════════
#  P10: 数据
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=2)
add_title(slide, "三大数据源")
add_body(slide, """mem.gov.cn 应急管理部          微信公众号                    PubChem
  全量95个月度汇编页              74篇事故分析文章               29种危化品物性
  1,261份事故报告（月度简报）       含安全建议 & 教训反思           CAS / IUPAC / 分子量
  BeautifulSoup 解析                108筛→74篇保存                  闪点 / 爆炸极限

数据处理：爬虫 → 文本清洗 → 多源融合 → 统一视图 (1,813行 × 19列)""",
         top=Inches(1.6), size=Pt(18))
add_notes(slide, "三个来源。微信文章是Mitigation主要来源。mem简报一事一报150字。PubChem标准化数据。")

# ═══════════════════════════════════════════════════════════
#  P11: 分隔页
# ═══════════════════════════════════════════════════════════
slide = new_slide(with_dots=False)
add_section(slide, 2, "实验评测", "数据规模 · 对照实验 · 洞察发现")
add_notes(slide, "赵乐毅：实验")

# ═══════════════════════════════════════════════════════════
#  P12: 数据规模
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=3)
add_title(slide, "最终数据规模")
add_chart(slide, '05_node_types.png', Inches(0.3), Inches(1.5), Inches(6.2), Inches(5.5))
# Right panel
add_body(slide, """6,976 节点 | 23,111 关系 | 1,579 事故

关键提升（v0.7）：
  Mitigation  4 → 71（18x）
  Accident    0 → 1,579（全新）
  Abnormal占比 67% → 51%（事件原子化）

节点分布：
  Abnormal 3,570 | Accident 1,579
  Equipment 688 | Consequence 641
  Material 427 | Mitigation 71""",
         left=Inches(7), top=Inches(1.8), size=Pt(15))
add_notes(slide, "数据规模。Mitigation和Accident是v0.7的核心提升。Abnormal占比下降说明Prompt原子化生效。")

# ═══════════════════════════════════════════════════════════
#  P13: 实验设计
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=3)
add_title(slide, '对照实验：三组Baseline → 回答“KG有没有必要？”')
add_body(slide, """关键词 RAG              Graph RAG              纯 LLM
  jieba + SQLite文本检索    KG因果路径约束          无外部数据
  → LLM回答                → 约束生成+来源引用       → 凭参数知识回答
  非结构化约束              结构化约束                无约束

20题 × 7种模式 × 3 baseline × 4维评估
  无幻觉率 | 来源可追溯率 | 节点命中率 | 诚实拒答率

核心问题：结构化约束（Graph RAG）是否优于非结构化约束（关键词RAG）和无约束（纯LLM）？""",
         top=Inches(1.4), size=Pt(16))
add_notes(slide, "三组对比。不是简单的ABC排序——每个baseline回答一个不同的问题。结构化 vs 非结构化 vs 无约束。")

# ═══════════════════════════════════════════════════════════
#  P14: 结果（核心）
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=3)
add_title(slide, "实验结果：Graph RAG 减少 9 倍幻觉")
add_chart(slide, '07_experiment.png', Inches(0.5), Inches(1.5), Inches(12.3), Inches(5.5))
add_notes(slide, "最重要的一页。9倍幻觉差距。诚实拒答55% vs 0%。纯LLM从不拒答——在安全领域致命。多停、多解释。")

# ═══════════════════════════════════════════════════════════
#  P15: 类型+时间
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=3)
add_title(slide, "洞察：事故类型与时间趋势")
add_chart(slide, '01_accident_types.png', Inches(0.3), Inches(1.5), Inches(6.2), Inches(5.5))
add_chart(slide, '02_timeline.png', Inches(6.8), Inches(1.5), Inches(6.2), Inches(5.5))
add_notes(slide, "爆炸61%+中毒27%=88%。2010s高峰616→2020s下降128。与2016年安全综合治理时间点吻合。")

# ═══════════════════════════════════════════════════════════
#  P16: 化学品+设备
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=3)
add_title(slide, "洞察：化学品与设备频次")
add_chart(slide, '03_chemicals.png', Inches(0.3), Inches(1.5), Inches(6.2), Inches(5.5))
add_chart(slide, '04_equipment.png', Inches(6.8), Inches(1.5), Inches(6.2), Inches(5.5))
add_notes(slide, "H2S 49起第一。N2 43起——无毒但窒息。反应釜62起遥——高温高压化学反应三位一体。")

# ═══════════════════════════════════════════════════════════
#  P17: 危险状态
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=3)
add_title(slide, "洞察：最危险中间异常状态")
add_chart(slide, '06_dangerous_states.png', Inches(0.8), Inches(1.5), Inches(11.5), Inches(5.5))
add_notes(slide, "形成爆炸性混合气体→102后果。前8名5个与可燃气相关。控制一个环节阻断最多事故链。")

# ═══════════════════════════════════════════════════════════
#  P18: 分隔页
# ═══════════════════════════════════════════════════════════
slide = new_slide(with_dots=False)
add_section(slide, 3, "系统演示", "Streamlit Web应用 · 因果推理问答 · 可视化")
add_notes(slide, "翟彝凡：演示")

# ═══════════════════════════════════════════════════════════
#  P19: 问答演示
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=4)
add_title(slide, "演示：因果推理问答")
add_body(slide, """示例问题："反应釜温度失控如何导致爆炸？"
         （KG中真实存在因果链）

流程：三层匹配 → 定位实体 → Cypher检索4条因果路径 → 约束生成

回答结构：
  【事故链条概述】温度升高 → 反应加速 → 压力超标 → 爆炸 [路径1]
  【关键节点】压力超标是临界点——超过设计压力即不可逆 [路径2]
  【安全建议】增设紧急泄压系统、完善冷却水双电源配置 [路径1,3]

[ 现场操作录屏 / 截图 ]""",
         top=Inches(1.6), size=Pt(17))
add_notes(slide, "现场演示。提前预演一遍。案例选反应釜温度失控——KG里因果链最完整的问题之一。")

# ═══════════════════════════════════════════════════════════
#  P20: 可视化
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=4)
add_title(slide, "演示：因果路径可视化 & 数据仪表盘")
add_body(slide, """因果路径有向图                       数据分析仪表盘
  ● Equipment (绿方) →                  6种图表实时切换：
  ▲ Abnormal (橙三角) →                  事故趋势 / 类型饼图 /
  ✕ Consequence (红叉) →                 化学品频次 / 设备频次 /
  ★ Mitigation (紫星)                    图谱桑基图 / 地区分布
  节点类型&颜色一一对应                   全部从SQLite+Neo4j实时生成

[ 截图 / 现场切换演示 ]""",
         top=Inches(1.6), size=Pt(17))
add_notes(slide, "路径可视化展示完整因果链。仪表盘六种视图实时切换。")

# ═══════════════════════════════════════════════════════════
#  P21: 分隔页
# ═══════════════════════════════════════════════════════════
slide = new_slide(with_dots=False)
add_section(slide, 4, "收获与展望", "技术心得 · 未来方向")
add_notes(slide, "赵乐毅 + 余亮阳")

# ═══════════════════════════════════════════════════════════
#  P22: 收获
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=5)
add_title(slide, "三个核心收获")
add_body(slide, """1. Prompt工程是精细的迭代科学
   不是一次写对——是看不下去→改规则→跑数据→再看不下去→几十轮
   每条规则的名字你知道它要解决什么问题：事件原子化、人员分离、设备优先

2. 双存储不是过度设计，是各司其职
   图数据库做因果链天然匹配，关系数据库做统计简洁高效
   "A导致B"在Neo4j一行MERGE，在SQL需要复杂JOIN

3. "LLM建KG + KG约束LLM" —— 有实验证据的闭环
   不是"看起来不错"，是"数据说比纯LLM少9倍幻觉，且能诚实拒答"
   在安全领域，可信 > 华丽""",
         top=Inches(1.2), size=Pt(17))
add_notes(slide, "三条收获。强调迭代——不是灵光一现，是归纳。强调证据——不是感觉，是数据。")

# ═══════════════════════════════════════════════════════════
#  P23: 未来
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=5)
add_title(slide, '未来工作：从“回溯”走向“预测”')
add_body(slide, """数据源扩展 — CSB英文调查报告（完整安全建议章节）
            → 显著提升Mitigation节点数量和因果链深度

实体消歧 — "形成爆炸性混合气体"与"形成爆炸性混合物"自动合并
          → 提升图谱连通性和查询覆盖

多语言 — 接入eMARS欧盟数据库 + CSB英文报告
        → 跨语言事故模式对比

风险预测 — 从"发生过什么"走向"什么可能会发生"
          → 基于历史数据训练模型，预测设备故障概率""",
         top=Inches(1.5), size=Pt(18))
add_notes(slide, "四个方向。CSB是第一优先级——全世界最完整的化工事故调查报告。")

# ═══════════════════════════════════════════════════════════
#  P24: 分隔页
# ═══════════════════════════════════════════════════════════
slide = new_slide(with_dots=False)
add_section(slide, 5, "总结", "")
add_notes(slide, "翟彝凡：总结")

# ═══════════════════════════════════════════════════════════
#  P25: 总结
# ═══════════════════════════════════════════════════════════
slide = new_slide(section=5)
add_title(slide, "四句话总结")
add_body(slide, """成果 — 首个大规模中文化工安全事故知识图谱
       1,579起事故 | 6,976节点 | 23,111关系边 | 已开源发布

方法 — Prompt Chain自动构建 + Graph RAG因果约束
       LLM与KG的闭环系统

证据 — 三组对照实验，20组测试题
       Graph RAG比纯LLM减少9倍幻觉，诚实拒答55%

结论 — 在化工安全领域，知识图谱不是可选项
       它不只让回答更好，而是让回答值得信任""",
         top=Inches(1.2), size=Pt(19))
add_notes(slide, "四句话。成果→方法→证据→结论。每句可独立成立。")

# ═══════════════════════════════════════════════════════════
#  P26: 感谢
# ═══════════════════════════════════════════════════════════
slide = new_slide(with_dots=False)
txBox = slide.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10), Inches(3.5))
tf = txBox.text_frame
p = tf.paragraphs[0]; p.text = "感谢聆听"; p.font.size = Pt(56); p.font.bold = True; p.font.color.rgb = C_ACCENT; p.alignment = PP_ALIGN.CENTER
p2 = tf.add_paragraph(); p2.text = "欢迎提问 & 交流讨论"; p2.font.size = Pt(24); p2.font.color.rgb = C_GREY; p2.alignment = PP_ALIGN.CENTER
p3 = tf.add_paragraph(); p3.text = ""; p3.font.size = Pt(14)
p4 = tf.add_paragraph(); p4.text = "数据集: CC BY-NC 4.0 开源"; p4.font.size = Pt(14); p4.font.color.rgb = C_GREY_DK; p4.alignment = PP_ALIGN.CENTER
add_notes(slide, "感谢王老师。Q&A。")


# ═══ Save ══════════════════════════════════════════════════
OUT_PATH = Path('D:/课程文件/大二下/数据库技术及应用/大作业/期末汇报材料/ChemSafe-KG_期末汇报.pptx')
prs.save(OUT_PATH)
print(f"PPT saved: {OUT_PATH}")
print(f"Slides: {len(prs.slides)}")
