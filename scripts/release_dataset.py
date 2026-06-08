"""
数据集发布脚本 v2.0

从 SQLite + Neo4j 导出全量数据:
  - accidents.csv（全量事故记录）
  - chemical_properties.csv（29种危化品物性）
  - causal_triples.csv（全部因果关系三元组，从 Neo4j 导出）
  - DATASET_CARD.md（v2.0，含数据规模、构建方法、使用限制）

前置条件: Neo4j + SQLite 均有数据
运行: python scripts/release_dataset.py
输出: data/release/
"""
import os, sys, json, csv, re
from pathlib import Path
from datetime import datetime

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("release")

import sqlite3
import pandas as pd

OUT_DIR = Path("data/release")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
#  1. 从 SQLite 导出 accidents + chemical_properties
# ═══════════════════════════════════════════════════════════════════════
def export_sqlite():
    conn = sqlite3.connect("data/processed/chemsafe.db")

    # accidents
    df = pd.read_sql("SELECT * FROM accidents", conn)
    df.to_csv(OUT_DIR / "accidents.csv", index=False, encoding="utf-8-sig")
    acc_count = len(df)
    date_ok = df["date"].notna().sum()
    root_ok = (df["root_cause"].notna() & (df["root_cause"] != "")).sum()
    cons_ok = (df["consequence"].notna() & (df["consequence"] != "")).sum()
    chem_ok = (df["related_chemicals"].notna() & (df["related_chemicals"] != "")).sum()
    equip_ok = (df["related_equipment"].notna() & (df["related_equipment"] != "")).sum()

    logger.info(f"accidents.csv: {acc_count} 条")
    logger.info(f"  date 完整: {date_ok}/{acc_count} ({100*date_ok/max(acc_count,1):.0f}%)")
    logger.info(f"  root_cause: {root_ok}/{acc_count}")
    logger.info(f"  consequence: {cons_ok}/{acc_count}")
    logger.info(f"  chemicals: {chem_ok}/{acc_count}")
    logger.info(f"  equipment: {equip_ok}/{acc_count}")

    # chemical_properties
    chem_df = pd.read_sql("SELECT * FROM chemical_properties", conn)
    chem_df.to_csv(OUT_DIR / "chemical_properties.csv", index=False, encoding="utf-8-sig")
    chem_count = len(chem_df)
    logger.info(f"chemical_properties.csv: {chem_count} 种")

    conn.close()
    return acc_count, date_ok, chem_count


# ═══════════════════════════════════════════════════════════════════════
#  2. 从 Neo4j 导出因果三元组
# ═══════════════════════════════════════════════════════════════════════
def export_neo4j_triples():
    """导出所有 leads_to / involves / mitigated_by 关系为三元组 CSV"""
    from src.storage.neo4j_client import Neo4jClient

    neo4j = Neo4jClient()
    neo4j.connect()
    if neo4j.graph is None:
        logger.error("Neo4j 未连接")
        return 0, 0

    # 导出三元组
    rows = neo4j.graph.run("""
        MATCH (s)-[r]->(t)
        WHERE type(r) IN ['leads_to', 'involves', 'mitigated_by']
          AND s.name IS NOT NULL AND t.name IS NOT NULL
        RETURN labels(s)[0] AS src_type, s.name AS src,
               type(r) AS rel,
               labels(t)[0] AS tgt_type, t.name AS tgt
    """).data()

    triples = [(r["src_type"], r["src"], r["rel"], r["tgt_type"], r["tgt"]) for r in rows]

    with open(OUT_DIR / "causal_triples.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["src_type", "src", "rel", "tgt_type", "tgt"])
        writer.writerows(triples)

    # 节点统计
    node_stats = neo4j.graph.run("""
        MATCH (n) WHERE size(labels(n))>0
        RETURN labels(n)[0] as l, count(*) as c ORDER BY c DESC
    """).data()
    total_nodes = sum(r["c"] for r in node_stats)
    total_rels = neo4j.graph.run("MATCH ()-[r]->() RETURN count(r) as c").data()[0]["c"]
    acc_count = neo4j.graph.run("MATCH (a:Accident) RETURN count(a) as c").data()[0]["c"]

    logger.info(f"causal_triples.csv: {len(triples)} 条")
    logger.info(f"Neo4j: {total_nodes} nodes, {total_rels} rels, {acc_count} Accident")

    return len(triples), total_nodes


# ═══════════════════════════════════════════════════════════════════════
#  3. 生成 DATASET_CARD v2.0
# ═══════════════════════════════════════════════════════════════════════
def generate_dataset_card(acc_count, date_ok, chem_count, triple_count, node_count):
    date_pct = 100 * date_ok / max(acc_count, 1)

    card = f"""# ChemSafe-KG 化工安全事故知识图谱数据集

> **版本**: v2.0 | **日期**: {datetime.now().strftime('%Y-%m-%d')} | **许可**: CC BY-NC 4.0（学术研究）

## 数据集概述

**首个大规模结构化中文化工安全事故知识图谱数据集。**

覆盖 {acc_count} 起事故的因果链条，从应急管理部（mem.gov.cn）全量月度汇编和微信公众号事故分析文章中，通过 LLM 驱动的 Prompt Chain 策略自动抽取构建。

## 文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| accidents.csv | {acc_count} | 事故主表（含 LLM 抽取的根原因与后果） |
| chemical_properties.csv | {chem_count} | 29 种危化品物性（PubChem） |
| causal_triples.csv | {triple_count} | 因果关系三元组（Neo4j 导出） |

## accidents.csv 字段

| 字段 | 完整率 | 说明 |
|------|--------|------|
| title | 100% | 事故标题 |
| date | {date_pct:.0f}% | 事故日期 |
| summary | 100% | 事故摘要（≤500字） |
| root_cause | 100% | LLM 抽取的根原因 |
| consequence | 100% | LLM 抽取的后果总结 |
| related_chemicals | ~39% | 涉及的化学品 |
| related_equipment | ~53% | 涉及的设备 |
| source_url | 100% | 数据来源标识 |

## causal_triples.csv 字段

| 字段 | 说明 |
|------|------|
| src_type | 源实体类型（Equipment/Material/Abnormal_Condition/Consequence/Mitigation） |
| src | 源实体名称 |
| rel | 关系类型（leads_to/involves/mitigated_by） |
| tgt_type | 目标实体类型 |
| tgt | 目标实体名称 |

## 构建方法

- **事故采集**: mem.gov.cn 全量月度汇编（1,261 份）+ 微信公众号（74 篇），BeautifulSoup 解析
- **知识抽取**: DeepSeek deepseek-v4-flash，Prompt Chain（5 实体类型 × 3 关系类型 + Few-shot），事件原子化约束
- **图存储**: Neo4j 5.26.25 Community，{node_count}+ 节点
- **化学品**: PubChem（pubchempy），29 种

## 使用限制

1. 数据源为月度汇编简报，非完整调查报告，描述较简略（平均 150 字）
2. LLM 抽取存在一定误差，因果链中个别节点可能偏离原文
3. 仅限学术研究和教育教学使用
4. 数据集持续更新中，当前版本可能非最终版

## 引用

```
@dataset{{chemsafe-kg-v2-{datetime.now().strftime('%Y')},
  title={{ChemSafe-KG v2.0: A Large-Scale Knowledge Graph Dataset for Chemical Accident Causal Analysis}},
  author={{Zhai, Yu, Zhao}},
  year={{{datetime.now().strftime('%Y')}}},
  note={{CC BY-NC 4.0, academic use only}}
}}
```

## 致谢

本项目为清华大学《数据库技术及应用》课程项目。感谢王健楠教授的指导。
"""
    (OUT_DIR / "DATASET_CARD.md").write_text(card, encoding="utf-8")
    logger.info(f"DATASET_CARD.md 已生成")


# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  ChemSafe-KG 数据集发布 v2.0")
    logger.info("=" * 60)

    acc_count, date_ok, chem_count = export_sqlite()
    triple_count, node_count = export_neo4j_triples()
    generate_dataset_card(acc_count, date_ok, chem_count, triple_count, node_count)

    logger.info(f"\n发布完成! 输出: {OUT_DIR}")
    for f in sorted(OUT_DIR.glob("*")):
        sz = f.stat().st_size
        logger.info(f"  {f.name:35s} {sz:>10,} bytes")
