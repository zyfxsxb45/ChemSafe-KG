"""
期末汇报图表生成脚本

生成高分辨率 PNG 图表用于 PPT：
  1. 事故类型分布（环形图）
  2. 事故时间趋势（柱状图）
  3. 化学品事故频次 Top 15（横向柱状图）
  4. 设备故障频次 Top 12（横向柱状图）
  5. 节点类型分布（环形图）
  6. 因果类型流转（桑基图）
  7. 对照实验结果对比表（图片化）
  8. 最危险中间异常状态 Top 8

输出目录: ../期末汇报材料/charts/
"""
import os, sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)
sys.path.insert(0, '.')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# 中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

OUT = Path('../期末汇报材料/charts')
OUT.mkdir(parents=True, exist_ok=True)

DPI = 200
COLORS = {
    'explosion': '#F44336', 'poison': '#FF9800', 'fire': '#FF5722',
    'leak': '#2196F3', 'collapse': '#795548', 'other': '#9E9E9E',
    'equipment': '#4CAF50', 'material': '#2196F3',
    'abnormal': '#FF9800', 'consequence': '#F44336',
    'mitigation': '#9C27B0', 'accident': '#607D8B',
    'keyword': '#2196F3', 'graph': '#4CAF50', 'llm': '#F44336',
}


# ═══════════════════════════════════════════════════════════════
#  1. 事故类型分布
# ═══════════════════════════════════════════════════════════════
def chart_accident_types():
    labels = ['爆炸', '中毒窒息', '火灾', '泄漏', '坍塌', '其他']
    values = [967, 424, 80, 41, 4, 63]
    colors_pie = [COLORS['explosion'], COLORS['poison'], COLORS['fire'],
                  COLORS['leak'], COLORS['collapse'], COLORS['other']]

    fig, ax = plt.subplots(figsize=(7, 6))
    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct='%1.1f%%', startangle=90,
        colors=colors_pie, pctdistance=0.75,
        wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2)
    )
    for t in autotexts:
        t.set_fontsize(14)
        t.set_fontweight('bold')
        t.set_color('white' if t.get_text().startswith('61') else '#333')

    legend_labels = [f'{l}  ({v}起)' for l, v in zip(labels, values)]
    ax.legend(wedges, legend_labels, loc='center left', bbox_to_anchor=(1, 0.5),
              fontsize=11, frameon=False)
    ax.set_title('事故类型分布', fontsize=18, fontweight='bold', pad=20)

    fig.tight_layout()
    fig.savefig(OUT / '01_accident_types.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print('  [1/8] 事故类型分布')


# ═══════════════════════════════════════════════════════════════
#  2. 时间趋势
# ═══════════════════════════════════════════════════════════════
def chart_timeline():
    decades = ['1940s', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
    counts = [5, 1, 3, 114, 153, 227, 616, 128]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    bars = ax.bar(decades, counts, color=['#E0E0E0' if c < 100 else '#F44336' for c in counts],
                  edgecolor='white', linewidth=0.8)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 8,
                str(count), ha='center', fontsize=12, fontweight='bold', color='#333')

    ax.set_ylabel('事故数量', fontsize=13)
    ax.set_title('事故时间分布（1947–2026）', fontsize=16, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylim(0, max(counts) * 1.15)
    ax.tick_params(axis='both', labelsize=12)

    # 标注关键信息
    ax.annotate(f'2010s 高峰: 616 起', xy=(6, 616), xytext=(4.5, 640),
                fontsize=11, color='#F44336', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='#F44336', lw=1.5))

    fig.tight_layout()
    fig.savefig(OUT / '02_timeline.png', dpi=DPI, facecolor='white', edgecolor='none')
    plt.close()
    print('  [2/8] 时间趋势')


# ═══════════════════════════════════════════════════════════════
#  3. 化学品频次 Top 15
# ═══════════════════════════════════════════════════════════════
def chart_chemicals():
    chems = ['硫化氢', '氮气', '甲醇', '氢气', '煤气', '硝酸铵',
             '氯乙烯', '液化石油气', '导热油', '甲苯', '汽油', '双氧水',
             '原油', '液氯', '液氨']
    counts = [49, 43, 39, 33, 27, 24, 23, 21, 18, 17, 17, 17, 15, 14, 14]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    y_pos = range(len(chems))
    bars = ax.barh(y_pos, counts, color=COLORS['material'], edgecolor='white', height=0.7)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                str(count), va='center', fontsize=11, fontweight='bold')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(chems, fontsize=12)
    ax.invert_yaxis()
    ax.set_xlabel('事故数', fontsize=13)
    ax.set_title('事故涉及化学品频次 Top 15', fontsize=16, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='x', labelsize=11)

    fig.tight_layout()
    fig.savefig(OUT / '03_chemicals.png', dpi=DPI, facecolor='white', edgecolor='none')
    plt.close()
    print('  [3/8] 化学品频次')


# ═══════════════════════════════════════════════════════════════
#  4. 设备频次
# ═══════════════════════════════════════════════════════════════
def chart_equipment():
    eqs = ['反应釜', '管道', '盲板', '储罐', '安全阀', '阀门',
           '硫酸储罐', '电磁阀', '液氮-氢氟酸换热器', '水解釜', '酸性水罐', '氯乙烯气柜']
    counts = [62, 16, 16, 14, 11, 11, 9, 9, 8, 8, 7, 7]

    fig, ax = plt.subplots(figsize=(8, 5))
    y_pos = range(len(eqs))
    bars = ax.barh(y_pos, counts, color=COLORS['equipment'], edgecolor='white', height=0.7)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                str(count), va='center', fontsize=11, fontweight='bold')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(eqs, fontsize=12)
    ax.invert_yaxis()
    ax.set_xlabel('事故数', fontsize=13)
    ax.set_title('事故涉及设备频次 Top 12', fontsize=16, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUT / '04_equipment.png', dpi=DPI, facecolor='white', edgecolor='none')
    plt.close()
    print('  [4/8] 设备频次')


# ═══════════════════════════════════════════════════════════════
#  5. 节点类型分布
# ═══════════════════════════════════════════════════════════════
def chart_node_types():
    labels = ['Abnormal\nCondition', 'Accident', 'Equipment',
              'Consequence', 'Material', 'Mitigation']
    values = [3570, 1579, 688, 641, 427, 71]
    node_colors = [COLORS['abnormal'], COLORS['accident'], COLORS['equipment'],
                   COLORS['consequence'], COLORS['material'], COLORS['mitigation']]

    fig, ax = plt.subplots(figsize=(7, 6))
    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct='%1.1f%%', startangle=90,
        colors=node_colors, pctdistance=0.7,
        wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2)
    )
    for t in autotexts:
        t.set_fontsize(12)
        t.set_fontweight('bold')

    legend_labels = [f'{l}  ({v:,})' for l, v in zip(labels, values)]
    ax.legend(wedges, legend_labels, loc='center left', bbox_to_anchor=(1, 0.5),
              fontsize=11, frameon=False)
    ax.set_title('知识图谱节点类型分布', fontsize=18, fontweight='bold', pad=20)

    fig.tight_layout()
    fig.savefig(OUT / '05_node_types.png', dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print('  [5/8] 节点类型')


# ═══════════════════════════════════════════════════════════════
#  6. 最危险中间异常状态
# ═══════════════════════════════════════════════════════════════
def chart_dangerous_states():
    states = ['形成爆炸性\n混合气体', '氢气泄漏', '违规使用\n原螺栓', '违规动火\n作业',
              '形成爆炸性\n混合物', '产生火花', '遇点火源', '与空气形成\n爆炸性混合物']
    counts = [102, 85, 84, 83, 83, 78, 76, 74]

    fig, ax = plt.subplots(figsize=(9, 5))
    colors_grad = ['#B71C1C', '#D32F2F', '#E53935', '#F44336',
                   '#EF5350', '#E57373', '#EF9A9A', '#FFCDD2']
    bars = ax.bar(range(len(states)), counts, color=colors_grad, edgecolor='white', linewidth=0.8)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                str(count), ha='center', fontsize=12, fontweight='bold', color='#B71C1C')

    ax.set_xticks(range(len(states)))
    ax.set_xticklabels(states, fontsize=10)
    ax.set_ylabel('关联后果数', fontsize=13)
    ax.set_title('最危险中间异常状态 Top 8', fontsize=16, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylim(0, max(counts) * 1.12)

    fig.tight_layout()
    fig.savefig(OUT / '06_dangerous_states.png', dpi=DPI, facecolor='white', edgecolor='none')
    plt.close()
    print('  [6/8] 危险状态')


# ═══════════════════════════════════════════════════════════════
#  7. 对照实验结果（分组柱状图）
# ═══════════════════════════════════════════════════════════════
def chart_experiment():
    metrics = ['无幻觉率\n(%)', '来源可追溯\n率 (%)', '节点命中\n率 (%)', '诚实拒答\n率 (%)']
    keyword = [40.0, 100.0, 30.6, 10.0]
    graph = [70.0, 55.0, 12.9, 55.0]
    pure_llm = [5.0, 0.0, 29.4, 0.0]

    # 平均幻觉数单独处理
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    # 左: 4项指标对比
    x = np.arange(len(metrics))
    w = 0.25
    b1 = ax1.bar(x - w, keyword, w, label='关键词RAG', color=COLORS['keyword'], edgecolor='white')
    b2 = ax1.bar(x, graph, w, label='Graph RAG', color=COLORS['graph'], edgecolor='white')
    b3 = ax1.bar(x + w, pure_llm, w, label='纯LLM', color=COLORS['llm'], edgecolor='white')

    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=10)
    ax1.set_ylabel('%', fontsize=13)
    ax1.set_title('四项指标对比', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10, frameon=False)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.set_ylim(0, 110)

    for bars in [b1, b2, b3]:
        for bar in bars:
            h = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2, h + 1,
                     f'{h:.0f}', ha='center', fontsize=8, fontweight='bold')

    # 右: 平均幻觉实体数
    methods = ['关键词RAG', 'Graph RAG', '纯LLM']
    halluc = [1.2, 0.65, 5.95]
    bar_colors = [COLORS['keyword'], COLORS['graph'], COLORS['llm']]
    bars = ax2.bar(methods, halluc, color=bar_colors, edgecolor='white', width=0.5)
    for bar, h in zip(bars, halluc):
        ax2.text(bar.get_x() + bar.get_width()/2, h + 0.1,
                 f'{h:.1f}', ha='center', fontsize=14, fontweight='bold', color='#333')
    ax2.set_title('平均幻觉实体数', fontsize=14, fontweight='bold')
    ax2.set_ylabel('个/题', fontsize=13)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.set_ylim(0, max(halluc) * 1.2)

    fig.tight_layout()
    fig.savefig(OUT / '07_experiment.png', dpi=DPI, facecolor='white', edgecolor='none')
    plt.close()
    print('  [7/8] 对照实验')


# ═══════════════════════════════════════════════════════════════
#  8. 系统架构图（文字版）
# ═══════════════════════════════════════════════════════════════
def chart_architecture():
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis('off')

    layers = [
        (5, 7.2, 'Streamlit Web 应用层', '问答交互 | 数据分析 | 图谱浏览 | 系统管理', '#37474F', 'white'),
        (4, 5.8, 'Graph RAG 问答层', '三层实体匹配 → 因果路径检索 → 约束生成 + 来源引用', '#1565C0', 'white'),
        (3, 4.4, '知识存储层', 'Neo4j 5.26 图数据库 + SQLite 关系数据库 + 跨源链接', '#2E7D32', 'white'),
        (2, 3.0, 'LLM 知识抽取层', 'DeepSeek v4-flash + Prompt Chain + JSON 三级容错', '#E65100', 'white'),
        (1, 1.6, '数据获取与预处理层', 'mem.gov.cn 爬虫 + 微信文章 + PubChem 化学品 + 文本清洗', '#6A1B9A', 'white'),
    ]

    for y, label_y, title, desc, bg, fg in layers:
        # layer box
        rect = plt.Rectangle((0.5, y), 9, 1.1, facecolor=bg, edgecolor='white',
                             linewidth=2, alpha=0.9, zorder=2)
        ax.add_patch(rect)
        ax.text(1, label_y, title, fontsize=13, fontweight='bold', color=fg,
                va='center', zorder=3)
        ax.text(1, label_y - 0.35, desc, fontsize=9, color=fg, alpha=0.85,
                va='center', zorder=3)

        # connecting lines
        if y < 5:
            for x_pos in [3, 7]:
                ax.annotate('', xy=(x_pos, y + 1.1), xytext=(x_pos, y + 1.45),
                            arrowprops=dict(arrowstyle='->', color='#BDBDBD', lw=1.5), zorder=1)

    # data icons
    ax.text(8.5, 4.0, '⛁ 6,976 节点\n⛗ 23,111 关系\n⛃ 1,579 事故\n⛖ 71 类措施',
            fontsize=9, ha='center', color='#333',
            bbox=dict(boxstyle='round', facecolor='#F5F5F5', edgecolor='#BDBDBD'))

    ax.set_title('ChemSafe-KG 系统架构', fontsize=18, fontweight='bold', pad=15)

    fig.tight_layout()
    fig.savefig(OUT / '08_architecture.png', dpi=DPI, facecolor='white', edgecolor='none')
    plt.close()
    print('  [8/8] 系统架构')

    print(f'\n全部图表已保存至: {OUT}')


if __name__ == '__main__':
    chart_accident_types()
    chart_timeline()
    chart_chemicals()
    chart_equipment()
    chart_node_types()
    chart_dangerous_states()
    chart_experiment()
    chart_architecture()
