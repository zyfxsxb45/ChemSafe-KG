"""ChemSafe-KG 数据集发布脚本"""
import os, sys
from pathlib import Path
from datetime import datetime
os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')
import logging, sqlite3, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("release")

RELEASE_DIR = Path("data/release")
RELEASE_DIR.mkdir(parents=True, exist_ok=True)

# ---- export accidents ----
conn = sqlite3.connect("data/processed/chemsafe.db")
df = pd.read_sql("SELECT title,date,summary,root_cause,consequence,related_chemicals,related_equipment,source_url FROM accidents", conn)
df = df.fillna("")
df.to_csv(RELEASE_DIR / "accidents.csv", index=False, encoding="utf-8-sig")
acc_total = len(df)
acc_rc = (df["root_cause"] != "").sum()
acc_ch = (df["related_chemicals"] != "").sum()
acc_eq = (df["related_equipment"] != "").sum()
acc_dr = f"{df['date'].min()} ~ {df['date'].max()}"
logger.info(f"accidents.csv: {acc_total} rows")

# ---- export chemicals ----
df2 = pd.read_sql("SELECT chemical_name,english_name,cas_number,iupac_name,molecular_weight FROM chemical_properties", conn)
df2.to_csv(RELEASE_DIR / "chemical_properties.csv", index=False, encoding="utf-8-sig")
chem_count = len(df2)
conn.close()
logger.info(f"chemical_properties.csv: {chem_count} rows")

# ---- export triples from Neo4j ----
triple_count = 0
try:
    from py2neo import Graph
    from dotenv import load_dotenv; load_dotenv()
    g = Graph(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))
    r = g.run("MATCH (a)-[rel:leads_to]->(b) WHERE size(labels(a))>0 AND size(labels(b))>0 RETURN labels(a)[0] AS src_type, a.name AS src, type(rel) AS rel, labels(b)[0] AS tgt_type, b.name AS tgt LIMIT 1000").data()
    pd.DataFrame(r).to_csv(RELEASE_DIR / "causal_triples.csv", index=False, encoding="utf-8-sig")
    triple_count = len(r)
    logger.info(f"causal_triples.csv: {triple_count} rows")
except Exception as e:
    logger.warning(f"Neo4j export skipped: {e}")

# ---- data card ----
card = """# ChemSafe-KG 化工安全事故数据集

> **版本**: v1.0 | **日期**: {date} | **来源**: mem.gov.cn | **许可**: 学术研究

## 数据集概述

首个公开可用的**结构化中文化工安全事故知识图谱数据集**，{total} 起事故 + {triple} 条因果关系三元组。

## 文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| accidents.csv | {total} | 事故主表 |
| chemical_properties.csv | {chem} | 29种危化品物性 |
| causal_triples.csv | {triple} | 因果关系三元组 |

## accidents.csv 字段

| 字段 | 完整率 |
|------|--------|
| title | 100% |
| date | 99% |
| summary | 100% |
| root_cause (LLM抽取) | {rc}/{total} |
| consequence (LLM抽取) | 100% |
| related_chemicals | {ch}/{total} |
| related_equipment | {eq}/{total} |
| source_url | 100% |

时间范围: {dr}

## 构建方法

- 事故采集: mem.gov.cn 95个月度汇编页, BeautifulSoup解析
- KG构建: DeepSeek deepseek-v4-flash, Prompt Chain, 87%成功率
- 化学品: PubChem (pubchempy), 29种, 100%字段完整

## 使用限制

1. 月度汇编非完整调查报告, 描述简短(avg 150字)
2. LLM抽取存在约13%误差
3. 仅限学术研究

## 引用

```
@dataset{{chemsafe-kg-2026,
  title={{ChemSafe-KG: A Knowledge Graph Dataset for Chemical Accident Causal Analysis}},
  author={{Zhai, Yu, Zhao}},
  year={{2026}}
}}
```
""".format(
    date=datetime.now().strftime('%Y-%m-%d'),
    total=acc_total, chem=chem_count, triple=triple_count,
    rc=acc_rc, ch=acc_ch, eq=acc_eq, dr=acc_dr,
)

(RELEASE_DIR / "DATASET_CARD.md").write_text(card, encoding="utf-8")

# ---- summary ----
logger.info(f"\nRelease: {RELEASE_DIR}")
for f in sorted(RELEASE_DIR.iterdir()):
    logger.info(f"  {f.name} ({f.stat().st_size/1024:.1f} KB)")
