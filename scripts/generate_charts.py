"""
期末汇报图表生成 v2 — 深色主题，匹配PPT风格

风格:
  - 背景 #0D1B2A (深蓝黑，与PPT一致)
  - 主色 #00B4D8 (青色强调)
  - 辅色 #F44336 / #4CAF50 / #FF9800 / #9C27B0 (实体类型色)
  - 白字灰标注，无边框，圆角

输出: D:/课程文件/大二下/数据库技术及应用/大作业/期末汇报材料/charts/
"""
import os; os.chdir(__import__('pathlib').Path(__file__).resolve().parent)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

OUT = Path('D:/课程文件/大二下/数据库技术及应用/大作业/期末汇报材料/charts')
OUT.mkdir(parents=True, exist_ok=True)

DPI = 200
BG = '#FFFFFF'
ACCENT = '#007BFF'
RED = '#DC3545'
GREEN = '#28A745'
ORANGE = '#E67E22'
PURPLE = '#6F42C1'
BLUE = '#007BFF'
WHITE = '#222222'
GREY = '#888888'
DARK_BG = '#F5F7FA'
HIGHLIGHT = '#E8F0FE'

STYLE = {
    'figure.facecolor': BG, 'axes.facecolor': BG,
    'axes.edgecolor': GREY, 'axes.labelcolor': WHITE,
    'text.color': WHITE, 'xtick.color': GREY, 'ytick.color': GREY,
    'grid.color': '#E0E0E0', 'grid.alpha': 0.5,
}
for k, v in STYLE.items():
    plt.rcParams[k] = v


def save(fig, name):
    fig.tight_layout(pad=2)
    fig.savefig(OUT / name, dpi=DPI, facecolor=BG, edgecolor='none',
                bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    print(f'  {name}')


# ═══════════════════════════════════════════════════════════
#  1. 节点类型分布（环形图）
# ═══════════════════════════════════════════════════════════
def chart_node_types():
    labels = ['Abnormal\nCondition', 'Accident', 'Equipment',
              'Consequence', 'Material', 'Mitigation']
    values = [3570, 1579, 688, 641, 427, 71]
    colors = [ORANGE, C_GREY if False else '#607D8B', GREEN, RED, BLUE, PURPLE]
    # Better palette matching entity types
    colors = [ORANGE, '#78909C', GREEN, RED, BLUE, PURPLE]

    fig, ax = plt.subplots(figsize=(8, 7), facecolor=BG)
    ax.set_facecolor(BG)
    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct='%1.1f%%', startangle=90,
        colors=colors, pctdistance=0.72,
        wedgeprops=dict(width=0.38, edgecolor=BG, linewidth=2.5)
    )
    for t in autotexts:
        t.set_fontsize(14); t.set_fontweight('bold')
        t.set_color(WHITE)

    legend_labels = [f'{l.replace(chr(10)," ")}  ({v:,})' for l, v in zip(labels, values)]
    leg = ax.legend(wedges, legend_labels, loc='center left',
                    bbox_to_anchor=(1.02, 0.5), fontsize=12,
                    frameon=False, labelcolor=WHITE,
                    handletextpad=0.8, borderpad=0.5)

    ax.set_title('知识图谱节点类型分布', fontsize=20, fontweight='bold',
                 color=WHITE, pad=25)
    # Total in center
    ax.text(0, 0, f'6,976', ha='center', va='center', fontsize=38,
            fontweight='bold', color=ACCENT)
    ax.text(0, -0.18, '节点总数', ha='center', va='center', fontsize=14, color=GREY)

    save(fig, '01_node_types.png')


# ═══════════════════════════════════════════════════════════
#  2. 事故类型分布（环形图）
# ═══════════════════════════════════════════════════════════
def chart_accident_types():
    labels = ['爆炸', '中毒窒息', '其他', '火灾', '泄漏', '坍塌']
    values = [530, 210, 311, 64, 58, 1]
    colors = [RED, ORANGE, GREY, '#FF5722', BLUE, '#795548']

    fig, ax = plt.subplots(figsize=(8, 7), facecolor=BG)
    ax.set_facecolor(BG)
    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct='%1.1f%%', startangle=90,
        colors=colors, pctdistance=0.72,
        wedgeprops=dict(width=0.38, edgecolor=BG, linewidth=2.5)
    )
    for t in autotexts:
        t.set_fontsize(14); t.set_fontweight('bold')
        t.set_color(WHITE)

    legend_labels = [f'{l}  ({v}起)' for l, v in zip(labels, values)]
    ax.legend(wedges, legend_labels, loc='center left',
              bbox_to_anchor=(1.02, 0.5), fontsize=12,
              frameon=False, labelcolor=WHITE)

    ax.set_title('事故类型分布', fontsize=20, fontweight='bold', color=WHITE, pad=25)
    ax.text(0, 0, f'{sum(values):,}', ha='center', va='center', fontsize=38,
            fontweight='bold', color=ACCENT)
    ax.text(0, -0.18, '事故总数', ha='center', va='center', fontsize=14, color=GREY)

    save(fig, '02_accident_types.png')


# ═══════════════════════════════════════════════════════════
#  3. 时间趋势（深色柱状图）
# ═══════════════════════════════════════════════════════════
def chart_timeline():
    decades = ['1940s', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
    counts = [4, 1, 2, 90, 108, 150, 398, 95]

    fig, ax = plt.subplots(figsize=(11, 5.5), facecolor=BG)
    ax.set_facecolor(BG)
    colors_bar = ['#AABBCC' if c < 200 else RED for c in counts]
    bars = ax.bar(decades, counts, color=colors_bar, edgecolor=BG, linewidth=0.8, width=0.7)

    for bar, count in zip(bars, counts):
        color = WHITE if count >= 200 else GREY
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                str(count), ha='center', fontsize=14, fontweight='bold', color=color)

    ax.set_ylabel('事故数量', fontsize=14, color=GREY)
    ax.set_title('事故时间分布（1947–2026）', fontsize=20, fontweight='bold',
                 color=WHITE, pad=15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(GREY)
    ax.spines['bottom'].set_color(GREY)
    ax.set_ylim(0, max(counts) * 1.25)
    ax.tick_params(axis='both', colors=GREY, labelsize=12)
    ax.yaxis.grid(True, color='#E0E0E0', alpha=0.5)
    ax.set_axisbelow(True)

    # Annotation
    ax.annotate(f'2010s 高峰: 616 起', xy=(6, 616), xytext=(4.2, 670),
                fontsize=12, color=RED, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=RED, lw=1.5))

    save(fig, '03_timeline.png')


# ═══════════════════════════════════════════════════════════
#  4. 化学品频次 Top 15
# ═══════════════════════════════════════════════════════════
def chart_chemicals():
    chems = ['硫化氢', '氮气', '甲醇', '氢气', '煤气', '硝酸铵',
             '氯乙烯', '液化石油气', '导热油', '甲苯', '汽油', '双氧水',
             '原油', '液氯', '液氨']
    counts = [30, 35, 28, 22, 21, 18, 17, 16, 14, 13, 13, 12, 12, 11, 11]

    fig, ax = plt.subplots(figsize=(9, 6), facecolor=BG)
    ax.set_facecolor(BG)
    y_pos = range(len(chems))
    bars = ax.barh(y_pos, counts, color=BLUE, edgecolor=BG, height=0.65, alpha=0.85)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                str(count), va='center', fontsize=12, fontweight='bold', color=WHITE)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(chems, fontsize=13, color=WHITE)
    ax.invert_yaxis()
    ax.set_xlabel('事故数', fontsize=14, color=GREY)
    ax.set_title('事故涉及化学品频次 Top 15', fontsize=20, fontweight='bold',
                 color=WHITE, pad=15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(GREY)
    ax.spines['bottom'].set_color(GREY)
    ax.tick_params(axis='x', colors=GREY, labelsize=11)
    ax.xaxis.grid(True, color='#E0E0E0', alpha=0.5)
    ax.set_axisbelow(True)

    save(fig, '04_chemicals.png')


# ═══════════════════════════════════════════════════════════
#  5. 设备频次 Top 12
# ═══════════════════════════════════════════════════════════
def chart_equipment():
    eqs = ['反应釜', '管道', '盲板', '储罐', '安全阀', '阀门',
           '硫酸储罐', '电磁阀', '换热器', '水解釜', '酸性水罐', '氯乙烯气柜']
    counts = [40, 13, 12, 10, 8, 8, 7, 7, 6, 6, 6, 5]

    fig, ax = plt.subplots(figsize=(9, 5.5), facecolor=BG)
    ax.set_facecolor(BG)
    y_pos = range(len(eqs))
    bars = ax.barh(y_pos, counts, color=GREEN, edgecolor=BG, height=0.65, alpha=0.85)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                str(count), va='center', fontsize=12, fontweight='bold', color=WHITE)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(eqs, fontsize=13, color=WHITE)
    ax.invert_yaxis()
    ax.set_xlabel('事故数', fontsize=14, color=GREY)
    ax.set_title('事故涉及设备频次 Top 12', fontsize=20, fontweight='bold',
                 color=WHITE, pad=15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(GREY)
    ax.spines['bottom'].set_color(GREY)
    ax.tick_params(axis='x', colors=GREY, labelsize=11)
    ax.xaxis.grid(True, color='#E0E0E0', alpha=0.5)
    ax.set_axisbelow(True)

    save(fig, '05_equipment.png')


# ═══════════════════════════════════════════════════════════
#  6. 最危险异常状态 Top 8
# ═══════════════════════════════════════════════════════════
def chart_dangerous_states():
    states = ['形成爆炸性\n混合气体', '氢气泄漏', '违规使用\n原螺栓', '违规动火\n作业',
              '形成爆炸性\n混合物', '产生火花', '遇点火源', '与空气形成\n爆炸性混合物']
    counts = [102, 85, 84, 83, 83, 78, 76, 74]
    gradient = ['#FF1744', '#F44336', '#E53935', '#EF5350',
                '#E57373', '#EF9A9A', '#FFCDD2', '#FFEBEE']

    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=BG)
    ax.set_facecolor(BG)
    bars = ax.bar(range(len(states)), counts, color=gradient, edgecolor=BG,
                  linewidth=0.5, width=0.6, alpha=0.9)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                str(count), ha='center', fontsize=14, fontweight='bold', color=RED)

    ax.set_xticks(range(len(states)))
    ax.set_xticklabels(states, fontsize=10, color=WHITE)
    ax.set_ylabel('关联后果数', fontsize=14, color=GREY)
    ax.set_title('最高频中间异常状态 Top 8', fontsize=20, fontweight='bold',
                 color=WHITE, pad=15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(GREY)
    ax.spines['bottom'].set_color(GREY)
    ax.set_ylim(0, max(counts) * 1.18)
    ax.tick_params(axis='both', colors=GREY, labelsize=11)
    ax.yaxis.grid(True, color='#E0E0E0', alpha=0.5)
    ax.set_axisbelow(True)

    save(fig, '06_dangerous_states.png')


# ═══════════════════════════════════════════════════════════
#  7. 对照实验（分组柱状图，深色主题）
# ═══════════════════════════════════════════════════════════
def chart_experiment():
    metrics = ['图内约束率\n(%)', '来源可追溯\n率 (%)', '节点命中\n率 (%)', '诚实拒答\n率 (%)']
    keyword = [40.0, 100.0, 30.6, 10.0]
    graph = [70.0, 55.0, 12.9, 55.0]
    pure_llm = [5.0, 0.0, 29.4, 0.0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), facecolor=BG)
    for ax in [ax1, ax2]:
        ax.set_facecolor(BG)
        for spine in ax.spines.values():
            spine.set_color(GREY)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    # Left: 4 metrics
    x = np.arange(len(metrics))
    w = 0.25
    b1 = ax1.bar(x - w, keyword, w, label='关键词RAG', color=BLUE, edgecolor=BG, linewidth=0.5)
    b2 = ax1.bar(x, graph, w, label='Graph RAG', color=GREEN, edgecolor=BG, linewidth=0.5)
    b3 = ax1.bar(x + w, pure_llm, w, label='纯LLM', color=RED, edgecolor=BG, linewidth=0.5)

    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=10, color=WHITE)
    ax1.set_ylabel('%', fontsize=14, color=GREY)
    ax1.set_title('四项指标对比', fontsize=16, fontweight='bold', color=WHITE, pad=15)
    ax1.legend(fontsize=11, frameon=False, labelcolor=WHITE, loc='upper right')
    ax1.set_ylim(0, 115)
    ax1.tick_params(axis='y', colors=GREY, labelsize=10)
    ax1.yaxis.grid(True, color='#E0E0E0', alpha=0.5)
    ax1.set_axisbelow(True)

    for barset, offset in [(b1, -w), (b2, 0), (b3, w)]:
        for bar in barset:
            h = bar.get_height()
            if h > 0:
                ax1.text(bar.get_x() + bar.get_width()/2, h + 1.5,
                         f'{h:.0f}', ha='center', fontsize=9, fontweight='bold', color=WHITE)

    # Right: avg hallucinations
    methods = ['关键词RAG', 'Graph RAG', '纯LLM']
    halluc = [1.2, 0.65, 5.95]
    bar_colors = [BLUE, GREEN, RED]
    bars = ax2.bar(methods, halluc, color=bar_colors, edgecolor=BG, linewidth=0.5, width=0.5)
    for bar, h in zip(bars, halluc):
        ax2.text(bar.get_x() + bar.get_width()/2, h + 0.15,
                 f'{h:.1f}', ha='center', fontsize=16, fontweight='bold', color=WHITE)
    ax2.set_title('平均图谱外实体数', fontsize=16, fontweight='bold', color=WHITE, pad=15)
    ax2.set_ylabel('个/题', fontsize=14, color=GREY)
    ax2.set_ylim(0, max(halluc) * 1.25)
    ax2.tick_params(axis='y', colors=GREY, labelsize=10)
    ax2.tick_params(axis='x', colors=WHITE, labelsize=12)
    ax2.yaxis.grid(True, color='#E0E0E0', alpha=0.5)
    ax2.set_axisbelow(True)

    save(fig, '07_experiment.png')


# ═══════════════════════════════════════════════════════════
#  8. 系统架构图（深色主题信息图）
# ═══════════════════════════════════════════════════════════
def chart_architecture():
    fig, ax = plt.subplots(figsize=(11, 7), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 12); ax.set_ylim(0, 9); ax.axis('off')

    layers = [
        (1.5, 'Streamlit Web 应用层', '问答交互 · 数据分析 · 图谱浏览 · 系统管理', '#37474F'),
        (3.0, 'Graph RAG 问答层', '三层实体匹配 → 因果路径检索 → 约束生成 + 来源引用', '#1565C0'),
        (4.5, '知识存储层', 'Neo4j 5.26 图数据库 + SQLite + 跨源链接', '#2E7D32'),
        (6.0, 'LLM 知识抽取层', 'DeepSeek v4-flash + Prompt Chain + JSON 三级容错', '#E65100'),
        (7.5, '数据获取与预处理层', 'mem.gov.cn 爬虫 + 微信文章 + PubChem 化学品 + 文本清洗', '#6A1B9A'),
    ]

    for y, title, desc, color in layers:
        rect = plt.Rectangle((0.8, y - 0.5), 10, 1, facecolor=color, edgecolor=BG,
                             linewidth=3, alpha=0.88, zorder=2)
        ax.add_patch(rect)
        ax.text(1.2, y + 0.08, title, fontsize=15, fontweight='bold', color=WHITE,
                va='center', zorder=3)
        ax.text(1.2, y - 0.32, desc, fontsize=10, color='#B0BEC5', va='center', zorder=3)

        if y < 7.5:
            for x_pos in [3.5, 8.5]:
                ax.annotate('', xy=(x_pos, y + 0.5), xytext=(x_pos, y + 0.8),
                            arrowprops=dict(arrowstyle='->', color='#37474F', lw=2),
                            zorder=1)

    # Stats box
    rect = plt.Rectangle((9.2, 3.8), 2.4, 2.2, facecolor=DARK_BG, edgecolor=ACCENT,
                         linewidth=1, alpha=0.9, zorder=3)
    ax.add_patch(rect)
    stats_text = '6,976 节点\n23,111 关系\n1,174 事故\n71 条措施\n图谱外实体\n5.95→0.65'
    ax.text(10.4, 4.9, stats_text, fontsize=12, ha='center', va='center',
            color=WHITE, linespacing=1.8, zorder=4, fontweight='bold')

    ax.set_title('ChemSafe-KG 系统架构', fontsize=22, fontweight='bold', color=WHITE, pad=25)

    save(fig, '08_architecture.png')


# ═══════════════════════════════════════════════════════════
if __name__ == '__main__':
    print('Generating charts...')
    chart_node_types()
    chart_accident_types()
    chart_timeline()
    chart_chemicals()
    chart_equipment()
    chart_dangerous_states()
    chart_experiment()
    chart_architecture()
    print(f'\nDone. Output: {OUT}')
