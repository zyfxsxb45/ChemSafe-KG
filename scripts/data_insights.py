"""
数据洞察分析脚本

从 SQLite + Neo4j 中挖掘有洞察力的发现，输出 Markdown 报告。

分析维度:
  1. 事故时空分布（年份趋势、省份热力）
  2. 化学品-事故关联矩阵
  3. 设备故障频次与级联模式
  4. 事故类型与归因统计
  5. 图谱拓扑特征（度中心性、桥接节点、因果深度）
  6. 最危险中间异常状态排名

前置条件: SQLite + Neo4j 均有数据
运行: python scripts/data_insights.py
输出: data/processed/data_insights.md
"""
import os, sys, re
from pathlib import Path
from datetime import datetime
from collections import Counter

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("insights")

import sqlite3
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════
def analyze_temporal(db_path: str) -> str:
    """事故时间分布分析"""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT date, title FROM accidents WHERE date IS NOT NULL", conn)
    conn.close()

    if df.empty:
        return "暂无日期数据"

    df["year"] = pd.to_datetime(df["date"]).dt.year
    yearly = df.groupby("year").size().sort_index()

    # 只保留有效年份范围
    yearly = yearly[(yearly.index >= 1940) & (yearly.index <= 2026)]

    lines = []
    lines.append("### 1. 事故时间分布\n")
    lines.append(f"共 {len(df)} 起事故有明确日期，时间跨度 {int(yearly.index.min())}–{int(yearly.index.max())}。\n")

    if len(yearly) > 0:
        peak_year = yearly.idxmax()
        peak_count = yearly.max()
        recent_10 = yearly[yearly.index >= 2017]
        recent_total = recent_10.sum()
        lines.append(f"事故高峰年: **{int(peak_year)}**（{peak_count} 起）。\n")
        if len(recent_10) > 0:
            lines.append(f"2017–2026 年共 {recent_total} 起，最近峰值在 {int(recent_10.idxmax())}。\n")
        lines.append(f"\n| 年代 | 事故数 |\n|------|--------|")
        for decade_start in range(int(yearly.index.min()) // 10 * 10, 2030, 10):
            decade_end = decade_start + 9
            decade_count = yearly[(yearly.index >= decade_start) & (yearly.index <= decade_end)].sum()
            if decade_count > 0:
                lines.append(f"| {decade_start}–{decade_end} | {decade_count} |")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
def analyze_chemicals(db_path: str) -> str:
    """化学品频次分析"""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT related_chemicals, title FROM accidents WHERE related_chemicals IS NOT NULL AND related_chemicals != ''", conn)
    conn.close()

    if df.empty:
        return "暂无化学品数据"

    chem_counter = Counter()
    for val in df["related_chemicals"]:
        for chem in str(val).split(","):
            chem = chem.strip()
            if len(chem) >= 2:
                chem_counter[chem] += 1

    top = chem_counter.most_common(20)

    lines = []
    lines.append("### 2. 化学品事故频次\n")
    lines.append(f"共 {len(df)} 起事故关联了化学品，涉及 {len(chem_counter)} 种不同化学品。\n")
    lines.append(f"\n| 排名 | 化学品 | 事故数 |\n|------|--------|--------|")
    for rank, (chem, count) in enumerate(top, 1):
        lines.append(f"| {rank} | {chem} | {count} |")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
def analyze_equipment(db_path: str) -> str:
    """设备故障频次分析"""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT related_equipment FROM accidents WHERE related_equipment IS NOT NULL AND related_equipment != ''", conn)
    conn.close()

    if df.empty:
        return "暂无设备数据"

    eq_counter = Counter()
    for val in df["related_equipment"]:
        for eq in str(val).split(","):
            eq = eq.strip()
            if len(eq) >= 2:
                eq_counter[eq] += 1

    top = eq_counter.most_common(15)

    lines = []
    lines.append("### 3. 设备故障频次\n")
    lines.append(f"共 {len(df)} 起事故关联了设备，涉及 {len(eq_counter)} 种不同设备。\n")
    lines.append(f"\n| 排名 | 设备 | 事故数 |\n|------|------|--------|")
    for rank, (eq, count) in enumerate(top, 1):
        lines.append(f"| {rank} | {eq} | {count} |")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
def analyze_accident_types(db_path: str) -> str:
    """事故类型归因分析"""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT title, root_cause, consequence FROM accidents", conn)
    conn.close()

    TYPE_KEYWORDS = {
        "爆炸": ["爆炸", "爆燃", "闪爆", "爆轰"],
        "中毒窒息": ["中毒", "窒息"],
        "火灾": ["火灾", "起火", "燃烧"],
        "泄漏": ["泄漏", "泄露", "逸散"],
        "坍塌": ["坍塌", "倒塌"],
    }
    type_counter = Counter()
    for _, row in df.iterrows():
        txt = f"{row['title']} {row['root_cause']} {row['consequence']}"
        matched = False
        for typ, keywords in TYPE_KEYWORDS.items():
            if any(kw in txt for kw in keywords):
                type_counter[typ] += 1
                matched = True
                break
        if not matched:
            type_counter["其他"] += 1

    lines = []
    lines.append("### 4. 事故类型分布\n")
    lines.append(f"\n| 类型 | 事故数 | 占比 |\n|------|--------|------|")
    total = sum(type_counter.values())
    for typ, count in type_counter.most_common():
        lines.append(f"| {typ} | {count} | {100*count/total:.1f}% |")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
def analyze_neo4j_topology() -> str:
    """知识图谱拓扑分析"""
    from src.storage.neo4j_client import Neo4jClient
    neo4j = Neo4jClient()
    neo4j.connect()
    if neo4j.graph is None:
        return "Neo4j 未连接"

    lines = []
    lines.append("### 5. 知识图谱拓扑特征\n")

    # 度中心性 Top 15
    r = neo4j.graph.run("""
        MATCH (n)-[r:leads_to]->()
        WHERE size(labels(n)) > 0
        WITH n, count(r) as out_degree
        OPTIONAL MATCH ()-[r2:leads_to]->(n)
        WITH n, out_degree, count(r2) as in_degree
        RETURN labels(n)[0] as type, n.name as name, out_degree, in_degree, (out_degree + in_degree) as total
        ORDER BY total DESC LIMIT 15
    """).data()

    lines.append("#### 度中心性 Top 15（因果网络中最关键的节点）\n")
    lines.append(f"| 排名 | 节点 | 类型 | 出度 | 入度 | 总度 |")
    lines.append(f"|------|------|------|------|------|------|")
    for i, row in enumerate(r, 1):
        lines.append(f"| {i} | {row['name'][:30]} | {row['type']} | {row['out_degree']} | {row['in_degree']} | {row['total']} |")

    # 桥接节点（连接多种实体类型）
    r = neo4j.graph.run("""
        MATCH (n)-[:leads_to]->(m)
        WHERE size(labels(n)) > 0 AND size(labels(m)) > 0
        WITH n, collect(DISTINCT labels(m)[0]) as target_types
        WHERE size(target_types) >= 2
        RETURN labels(n)[0] as type, n.name as name, target_types, size(target_types) as diversity
        ORDER BY diversity DESC LIMIT 10
    """).data()

    if r:
        lines.append("\n#### 桥接节点（连接多种实体类型的关键枢纽）\n")
        lines.append(f"| 节点 | 类型 | 连接类型数 | 连接的类型 |")
        lines.append(f"|------|------|-----------|-----------|")
        for row in r:
            lines.append(f"| {row['name'][:35]} | {row['type']} | {row['diversity']} | {', '.join(row['target_types'][:4])} |")

    # 因果深度分布
    r = neo4j.graph.run("""
        MATCH path = ()-[:leads_to*1..6]->()
        WITH length(path) as depth, count(*) as cnt
        RETURN depth, cnt ORDER BY depth
    """).data()

    if r:
        lines.append("\n#### 因果链深度分布\n")
        lines.append(f"| 深度 | 路径数 | 说明 |")
        lines.append(f"|------|--------|------|")
        for row in r:
            desc = "单步因果" if row['depth'] == 1 else ("两步" if row['depth'] == 2 else f"{row['depth']}步级联")
            lines.append(f"| {row['depth']} | {row['cnt']} | {desc} |")

    # 最危险异常状态（指向最多后果的 Abnormal_Condition）
    r = neo4j.graph.run("""
        MATCH (n)-[:leads_to*1..3]->(c:Consequence)
        WHERE n:Abnormal_Condition
        WITH n, count(DISTINCT c) as consequence_count
        ORDER BY consequence_count DESC LIMIT 10
        RETURN n.name as name, consequence_count
    """).data()

    if r:
        lines.append("\n### 6. 最危险中间异常状态\n")
        lines.append("以下 Abnormal_Condition 节点关联最多的事故后果，是事故链条中最关键的薄弱环节：\n")
        lines.append(f"| 排名 | 异常状态 | 关联后果数 |")
        lines.append(f"|------|----------|-----------|")
        for i, row in enumerate(r, 1):
            lines.append(f"| {i} | {row['name'][:40]} | {row['consequence_count']} |")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
def analyze_overview(db_path: str) -> str:
    """数据概览"""
    conn = sqlite3.connect(db_path)
    total = conn.execute("SELECT count(*) FROM accidents").fetchone()[0]
    with_date = conn.execute("SELECT count(*) FROM accidents WHERE date IS NOT NULL").fetchone()[0]
    with_root = conn.execute("SELECT count(*) FROM accidents WHERE root_cause IS NOT NULL AND root_cause != ''").fetchone()[0]
    with_chem = conn.execute("SELECT count(*) FROM accidents WHERE related_chemicals IS NOT NULL AND related_chemicals != ''").fetchone()[0]
    with_equip = conn.execute("SELECT count(*) FROM accidents WHERE related_equipment IS NOT NULL AND related_equipment != ''").fetchone()[0]
    mem_count = conn.execute("SELECT count(*) FROM accidents WHERE source_url LIKE 'mem:%'").fetchone()[0]
    wx_count = conn.execute("SELECT count(*) FROM accidents WHERE source_url LIKE '微信:%'").fetchone()[0]
    conn.close()

    lines = []
    lines.append(f"## 数据概览\n")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 事故总数 | {total} |")
    lines.append(f"| 有日期 | {with_date} ({100*with_date/max(total,1):.0f}%) |")
    lines.append(f"| 有根原因 | {with_root} ({100*with_root/max(total,1):.0f}%) |")
    lines.append(f"| 有化学品 | {with_chem} ({100*with_chem/max(total,1):.0f}%) |")
    lines.append(f"| 有设备 | {with_equip} ({100*with_equip/max(total,1):.0f}%) |")
    lines.append(f"| 来源 mem.gov.cn | {mem_count} |")
    lines.append(f"| 来源 微信公众号 | {wx_count} |")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  ChemSafe-KG 数据洞察分析")
    logger.info("=" * 60)

    DB = "data/processed/chemsafe.db"
    if not Path(DB).exists():
        logger.error(f"数据库不存在: {DB}")
        sys.exit(1)

    sections = []

    logger.info("分析时间分布...")
    sections.append(analyze_temporal(DB))

    logger.info("分析化学品频次...")
    sections.append(analyze_chemicals(DB))

    logger.info("分析设备频次...")
    sections.append(analyze_equipment(DB))

    logger.info("分析事故类型...")
    sections.append(analyze_accident_types(DB))

    logger.info("分析图谱拓扑...")
    sections.append(analyze_neo4j_topology())

    # 组装 Markdown 报告
    overview = analyze_overview(DB)

    report = f"""# ChemSafe-KG 数据洞察报告

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

{overview}

{chr(10).join(sections)}

---

*本报告由 `scripts/data_insights.py` 自动生成。数据来源：SQLite + Neo4j。*
"""
    out_path = Path("data/processed/data_insights.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    logger.info(f"报告已保存: {out_path}")
