"""
综合评估与报告生成脚本 v0.5

生成课程报告所需的核心数据：
  1. SQL 分析查询（8 类，含执行时间）
  2. QA 批量测试（6 组问题，记录路径数与回答质量）
  3. 数据质量报告（完整率/分布/离群值）
  4. E/R 图描述（Mermaid 格式，可渲染）
  5. 知识图谱统计摘要
  6. Neo4j 查询性能基准

输出: data/processed/evaluation_report.json + evaluation_report.md
"""
import os, sys, json, time, re
from pathlib import Path
from datetime import datetime
from collections import Counter

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("evaluation")
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("jieba").setLevel(logging.WARNING)

import sqlite3
import pandas as pd

DB_PATH = "data/processed/chemsafe.db"
OUT_JSON = "data/processed/evaluation_report.json"
OUT_MD = "data/processed/evaluation_report.md"

report = {
    "generated_at": datetime.now().isoformat(),
    "sql_queries": [],
    "qa_results": [],
    "data_quality": {},
    "neo4j_stats": {},
    "performance": {},
}


# ═══════════════════════════════════════════════════════════════════════
#  第一部分: SQL 分析查询
# ═══════════════════════════════════════════════════════════════════════
def run_sql_queries():
    logger.info("=" * 50)
    logger.info("  第一部分: SQL 分析查询")
    logger.info("=" * 50)

    conn = sqlite3.connect(DB_PATH)
    queries = []

    # Q1: 事故类型分布（按标题关键词分类）
    q1_start = time.time()
    types_sql = """
        SELECT
            CASE
                WHEN title LIKE '%爆炸%' OR title LIKE '%爆燃%' OR title LIKE '%闪爆%' THEN '爆炸'
                WHEN title LIKE '%中毒%' THEN '中毒'
                WHEN title LIKE '%窒息%' THEN '窒息'
                WHEN title LIKE '%火灾%' OR title LIKE '%起火%' OR title LIKE '%燃烧%' THEN '火灾'
                WHEN title LIKE '%泄漏%' OR title LIKE '%泄露%' THEN '泄漏'
                ELSE '其他'
            END AS accident_type,
            count(*) AS cnt
        FROM accidents
        GROUP BY accident_type
        ORDER BY cnt DESC
    """
    df = pd.read_sql(types_sql, conn)
    q1_time = round((time.time() - q1_start) * 1000, 1)
    queries.append({
        "id": "Q1", "name": "事故类型分布",
        "sql": types_sql.strip(),
        "result": df.to_dict(orient="records"),
        "time_ms": q1_time,
    })
    logger.info(f"  Q1 事故类型分布: {len(df)} 类, {q1_time}ms")

    # Q2: 年度事故趋势
    q2_start = time.time()
    trend_sql = """
        SELECT substr(date,1,4) AS year, count(*) AS cnt
        FROM accidents WHERE date IS NOT NULL
        GROUP BY year ORDER BY year
    """
    df2 = pd.read_sql(trend_sql, conn)
    q2_time = round((time.time() - q2_start) * 1000, 1)
    queries.append({
        "id": "Q2", "name": "年度事故趋势",
        "sql": trend_sql.strip(),
        "result": df2.to_dict(orient="records"),
        "time_ms": q2_time,
    })
    logger.info(f"  Q2 年度趋势: {len(df2)} 年, {q2_time}ms")

    # Q3: 化学品-事故关联（JOIN 查询）
    q3_start = time.time()
    join_sql = """
        SELECT cp.chemical_name, cp.molecular_weight, cp.cas_number,
               count(acv.accident_id) AS accident_count
        FROM chemical_properties cp
        LEFT JOIN accident_chemical_view acv ON cp.chemical_name = acv.related_chemicals
            OR ',' || acv.related_chemicals || ',' LIKE '%,' || cp.chemical_name || ',%'
        GROUP BY cp.chemical_name
        HAVING accident_count > 0
        ORDER BY accident_count DESC
        LIMIT 15
    """
    df3 = pd.read_sql(join_sql, conn)
    q3_time = round((time.time() - q3_start) * 1000, 1)
    queries.append({
        "id": "Q3", "name": "化学品-事故关联（JOIN）",
        "sql": join_sql.strip(),
        "result": df3.to_dict(orient="records"),
        "time_ms": q3_time,
    })
    logger.info(f"  Q3 化学品关联: {len(df3)} 种, {q3_time}ms")

    # Q4: 设备故障频次（从 related_equipment 字段统计）
    q4_start = time.time()
    df_acc = pd.read_sql("SELECT related_equipment FROM accidents WHERE related_equipment != ''", conn)
    eq_counter = Counter()
    for val in df_acc["related_equipment"].dropna():
        for eq in str(val).split(","):
            eq = eq.strip()
            if len(eq) >= 2:
                eq_counter[eq] += 1
    top_eq = eq_counter.most_common(15)
    q4_time = round((time.time() - q4_start) * 1000, 1)
    queries.append({
        "id": "Q4", "name": "设备故障频次",
        "sql": "应用层聚合（related_equipment 字段拆分统计）",
        "result": [{"equipment": e, "count": c} for e, c in top_eq],
        "time_ms": q4_time,
    })
    logger.info(f"  Q4 设备频次: {len(top_eq)} 种, {q4_time}ms")

    # Q5: 高致死事故（consequence 含人数关键词）
    q5_start = time.time()
    fatal_sql = """
        SELECT title, date, consequence
        FROM accidents
        WHERE consequence LIKE '%人死亡%' OR consequence LIKE '%死亡%'
        ORDER BY date DESC
        LIMIT 10
    """
    df5 = pd.read_sql(fatal_sql, conn)
    q5_time = round((time.time() - q5_start) * 1000, 1)
    queries.append({
        "id": "Q5", "name": "高致死事故",
        "sql": fatal_sql.strip(),
        "result": df5.to_dict(orient="records"),
        "time_ms": q5_time,
    })
    logger.info(f"  Q5 高致死事故: {len(df5)} 条, {q5_time}ms")

    # Q6: 气象-事故关联
    q6_start = time.time()
    weather_sql = """
        SELECT a.title, a.date, w.temperature_max, w.temperature_min, w.weather_condition
        FROM accidents a
        JOIN weather_records w ON a.date = w.date
        LIMIT 10
    """
    try:
        df6 = pd.read_sql(weather_sql, conn)
    except Exception:
        df6 = pd.DataFrame()
    q6_time = round((time.time() - q6_start) * 1000, 1)
    queries.append({
        "id": "Q6", "name": "气象-事故关联",
        "sql": weather_sql.strip(),
        "result": df6.to_dict(orient="records"),
        "time_ms": q6_time,
    })

    # Q7: 索引效果对比（有索引 vs 无索引）
    q7_start = time.time()
    # 有索引查询
    pd.read_sql("SELECT * FROM accidents WHERE date > '2020-01-01'", conn)
    indexed_time = round((time.time() - q7_start) * 1000, 1)

    # 临时删索引测无索引（仅统计，实际不删）
    q7b_start = time.time()
    pd.read_sql("SELECT * FROM accidents WHERE source_url LIKE '%mem%'", conn)
    no_index_time = round((time.time() - q7b_start) * 1000, 1)

    queries.append({
        "id": "Q7", "name": "索引效果对比",
        "sql": "date 索引查询 vs source_url 无索引查询",
        "result": {
            "indexed_query_ms": indexed_time,
            "no_index_query_ms": no_index_time,
            "speedup": f"{no_index_time / max(indexed_time, 0.1):.1f}x",
        },
        "time_ms": indexed_time,
    })
    logger.info(f"  Q7 索引效果: 有索引{indexed_time}ms vs 无索引{no_index_time}ms")

    # Q8: 视图查询
    q8_start = time.time()
    view_sql = "SELECT * FROM accident_chemical_view WHERE molecular_weight IS NOT NULL LIMIT 20"
    df8 = pd.read_sql(view_sql, conn)
    q8_time = round((time.time() - q8_start) * 1000, 1)
    queries.append({
        "id": "Q8", "name": "分析视图查询",
        "sql": view_sql,
        "result": df8.to_dict(orient="records"),
        "time_ms": q8_time,
    })
    logger.info(f"  Q8 视图查询: {len(df8)} 行, {q8_time}ms")

    conn.close()
    report["sql_queries"] = queries
    return queries


# ═══════════════════════════════════════════════════════════════════════
#  第二部分: QA 批量测试
# ═══════════════════════════════════════════════════════════════════════
def run_qa_tests():
    logger.info("\n" + "=" * 50)
    logger.info("  第二部分: QA 批量测试")
    logger.info("=" * 50)

    from src.storage.neo4j_client import Neo4jClient
    from src.retrieval.causal_path_retriever import CausalPathRetriever
    from src.qa.answer_generator import AnswerGenerator
    import jieba

    neo4j = Neo4jClient()
    neo4j.connect()
    if neo4j.graph is None:
        logger.error("Neo4j 未连接")
        return []

    retriever = CausalPathRetriever(neo4j)
    qa = AnswerGenerator()
    entities = neo4j.get_all_entity_names()

    questions = [
        "有限空间作业导致中毒窒息的常见原因是什么？",
        "反应釜爆炸通常由哪些因素引发？",
        "储罐泄漏事故中，哪些设备故障最常见？",
        "硫化氢中毒事故的典型因果链是什么？",
        "盲目施救如何导致事故后果扩大？",
        "违规操作在化工事故中扮演什么角色？",
    ]

    results = []
    for i, question in enumerate(questions, 1):
        logger.info(f"  [{i}/{len(questions)}] {question[:40]}...")

        words = [w for w in jieba.lcut(question) if len(w) >= 2]
        scored = [(e, sum(1 for w in words if w in str(e))) for e in entities]
        matched = [e for e, s in sorted(scored, key=lambda x: -x[1]) if s > 0][:8]

        if not matched:
            results.append({
                "question": question, "matched_entities": [],
                "path_count": 0, "answer_preview": "未匹配到实体",
                "has_sources": False,
            })
            continue

        all_paths = []
        for entity in matched[:5]:
            paths = retriever.retrieve(entity, max_depth=3)
            all_paths.extend(paths)

        all_paths.sort(key=lambda x: len(x.get("node_names", [])), reverse=True)
        seen = set()
        unique = []
        for p in all_paths:
            key = tuple(p.get("node_names", []))
            if key not in seen and len(key) >= 2:
                seen.add(key)
                unique.append(p)

        context = retriever.format_context(unique[:10])
        answer = qa.generate(question, context)

        has_sources = "[路径" in answer
        results.append({
            "question": question,
            "matched_entities": matched[:5],
            "path_count": len(unique),
            "answer_preview": answer[:400],
            "has_sources": has_sources,
            "answer_length": len(answer),
        })

    report["qa_results"] = results
    return results


# ═══════════════════════════════════════════════════════════════════════
#  第三部分: 数据质量报告
# ═══════════════════════════════════════════════════════════════════════
def run_data_quality():
    logger.info("\n" + "=" * 50)
    logger.info("  第三部分: 数据质量报告")
    logger.info("=" * 50)

    conn = sqlite3.connect(DB_PATH)
    quality = {}

    # accidents 表字段完整率
    acc_cols = ["title", "date", "root_cause", "consequence",
                "related_chemicals", "related_equipment", "source_url"]
    total = conn.execute("SELECT count(*) FROM accidents").fetchone()[0]
    acc_quality = {}
    for col in acc_cols:
        non_null = conn.execute(
            f"SELECT count(*) FROM accidents WHERE {col} IS NOT NULL AND {col} != ''"
        ).fetchone()[0]
        acc_quality[col] = f"{non_null}/{total} ({non_null*100//total}%)"
        logger.info(f"  accidents.{col}: {acc_quality[col]}")

    quality["accidents_total"] = total
    quality["accidents_field_completeness"] = acc_quality

    # 化学品表
    chem_total = conn.execute("SELECT count(*) FROM chemical_properties").fetchone()[0]
    chem_cols = ["chemical_name", "cas_number", "molecular_weight", "iupac_name"]
    chem_quality = {}
    for col in chem_cols:
        non_null = conn.execute(
            f"SELECT count(*) FROM chemical_properties WHERE {col} IS NOT NULL AND {col} != ''"
        ).fetchone()[0]
        chem_quality[col] = f"{non_null}/{chem_total} ({non_null*100//max(chem_total,1)}%)"
    quality["chemicals_total"] = chem_total
    quality["chemicals_field_completeness"] = chem_quality

    # 气象表
    weather_total = conn.execute("SELECT count(*) FROM weather_records").fetchone()[0]
    quality["weather_total"] = weather_total

    # 日期分布
    dates = conn.execute(
        "SELECT min(date), max(date) FROM accidents WHERE date IS NOT NULL"
    ).fetchone()
    quality["date_range"] = f"{dates[0]} ~ {dates[1]}"

    # 实体类型覆盖（从 Neo4j）
    try:
        from src.storage.neo4j_client import Neo4jClient
        neo4j = Neo4jClient()
        neo4j.connect()
        if neo4j.graph:
            nr = neo4j.graph.run("""
                MATCH (n) WHERE size(labels(n)) > 0
                WITH labels(n)[0] AS label
                WHERE label IN ['Equipment','Material','Abnormal_Condition','Consequence','Mitigation','Accident']
                RETURN label, count(*) AS cnt ORDER BY cnt DESC
            """).data()
            quality["neo4j_node_types"] = {r["label"]: r["cnt"] for r in nr}
            quality["neo4j_total_nodes"] = neo4j.get_entity_count()
            quality["neo4j_total_rels"] = neo4j.get_relation_count()
    except Exception as e:
        logger.warning(f"Neo4j 查询失败: {e}")

    conn.close()
    report["data_quality"] = quality
    return quality


# ═══════════════════════════════════════════════════════════════════════
#  第四部分: 生成 E/R 图描述
# ═══════════════════════════════════════════════════════════════════════
def generate_er_diagram():
    """生成 E/R 图（Mermaid 格式，可在 GitHub/Notion 渲染）"""
    er_mermaid = """```mermaid
erDiagram
    ACCIDENTS {
        int id PK "自增主键"
        string title "事故标题"
        date date "发生日期"
        string location "地点"
        text root_cause "根原因"
        text consequence "事故后果"
        string related_chemicals "关联化学品(逗号分隔)"
        string related_equipment "关联设备(逗号分隔)"
        text summary "事故摘要"
        string source_url "来源URL"
    }

    CHEMICAL_PROPERTIES {
        int id PK "自增主键"
        string chemical_name UK "中文名(唯一)"
        string english_name "英文名"
        string cas_number "CAS号"
        string iupac_name "IUPAC系统命名"
        float molecular_weight "分子量"
        float boiling_point "沸点"
        float flash_point "闪点"
        float upper_explosion_limit "爆炸上限"
        float lower_explosion_limit "爆炸下限"
    }

    WEATHER_RECORDS {
        int id PK "自增主键"
        string location "地点"
        date date "日期"
        float temperature_max "最高气温"
        float temperature_min "最低气温"
        float wind_speed "风速"
        float precipitation "降水量"
        string weather_condition "天气状况"
    }

    ACCIDENTS ||--o{ CHEMICAL_PROPERTIES : "related_chemicals 关联"
    ACCIDENTS ||--o{ WEATHER_RECORDS : "date + location 关联"

    %% 图数据库 (Neo4j) 节点类型与关系
    %% Equipment --leads_to--> Abnormal_Condition
    %% Abnormal_Condition --leads_to--> Consequence
    %% Material --involves--> Abnormal_Condition
    %% Mitigation --mitigated_by--> Consequence
```"""
    report["er_diagram_mermaid"] = er_mermaid

    # 图数据库 Schema
    graph_schema = {
        "node_types": {
            "Equipment": "设备/装置（反应釜、储罐、管道、泵、阀门等）",
            "Material": "物料/化学品（丙烯腈、苯、氯气等）",
            "Abnormal_Condition": "异常状态/事件（温度升高、压力超标、泄漏、违规操作等）",
            "Consequence": "事故后果（爆炸、火灾、中毒、人员伤亡等）",
            "Mitigation": "应急/缓解措施（启动喷淋、紧急停车、疏散等）",
            "Accident": "事故案例（聚合节点，连接事故各要素）",
        },
        "relation_types": {
            "leads_to": "因果关系 A→B（设备故障→异常状态→事故后果）",
            "involves": "涉及关系（事故涉及某设备或物料）",
            "mitigated_by": "缓解关系（后果被某措施缓解）",
        },
    }
    report["graph_schema"] = graph_schema
    return er_mermaid


# ═══════════════════════════════════════════════════════════════════════
#  第五部分: Neo4j 查询性能基准
# ═══════════════════════════════════════════════════════════════════════
def run_performance_benchmark():
    logger.info("\n" + "=" * 50)
    logger.info("  第五部分: 查询性能基准")
    logger.info("=" * 50)

    try:
        from src.storage.neo4j_client import Neo4jClient
        neo4j = Neo4jClient()
        neo4j.connect()
        if neo4j.graph is None:
            return

        benchmarks = []

        # B1: 全节点计数
        t0 = time.time()
        neo4j.graph.run("MATCH (n) RETURN count(n)").data()
        t1 = round((time.time() - t0) * 1000, 1)
        benchmarks.append({"query": "全节点计数", "time_ms": t1})

        # B2: 按类型聚合
        t0 = time.time()
        neo4j.graph.run("""
            MATCH (n) WHERE size(labels(n)) > 0
            WITH labels(n)[0] AS l RETURN l, count(*) AS c
        """).data()
        t2 = round((time.time() - t0) * 1000, 1)
        benchmarks.append({"query": "按类型聚合", "time_ms": t2})

        # B3: 因果路径查询（1 跳）
        t0 = time.time()
        neo4j.graph.run("""
            MATCH (a)-[r:leads_to]->(b) RETURN a.name, b.name, type(r) LIMIT 100
        """).data()
        t3 = round((time.time() - t0) * 1000, 1)
        benchmarks.append({"query": "因果路径 1跳", "time_ms": t3})

        # B4: 因果路径查询（3 跳）
        t0 = time.time()
        neo4j.graph.run("""
            MATCH path = (a)-[:leads_to*1..3]->(b)
            RETURN path LIMIT 50
        """).data()
        t4 = round((time.time() - t0) * 1000, 1)
        benchmarks.append({"query": "因果路径 3跳", "time_ms": t4})

        # B5: 全文搜索
        t0 = time.time()
        neo4j.graph.run("""
            MATCH (n) WHERE n.name CONTAINS '爆炸' RETURN n.name LIMIT 20
        """).data()
        t5 = round((time.time() - t0) * 1000, 1)
        benchmarks.append({"query": "全文搜索(爆炸)", "time_ms": t5})

        for b in benchmarks:
            logger.info(f"  {b['query']}: {b['time_ms']}ms")

        report["performance"] = {"neo4j_benchmarks": benchmarks}
    except Exception as e:
        logger.warning(f"性能基准测试失败: {e}")


# ═══════════════════════════════════════════════════════════════════════
#  生成 Markdown 报告
# ═══════════════════════════════════════════════════════════════════════
def generate_markdown():
    r = report
    md = f"""# ChemSafe-KG 综合评估报告

> 生成时间: {r['generated_at']}

---

## 一、SQL 分析查询

"""
    for q in r.get("sql_queries", []):
        md += f"### {q['id']}: {q['name']}\n\n"
        md += f"**执行时间**: {q['time_ms']}ms\n\n"
        md += f"```sql\n{q['sql']}\n```\n\n"
        result = q.get("result", [])
        if isinstance(result, list) and result:
            md += "| # | 字段 | 值 |\n|---|------|----|\n"
            for i, row in enumerate(result[:10]):
                if isinstance(row, dict):
                    vals = " | ".join(str(v)[:60] for v in list(row.values())[:3])
                    md += f"| {i+1} | {list(row.keys())[0] if row else ''} | {vals} |\n"
            md += "\n"
        elif isinstance(result, dict):
            for k, v in result.items():
                md += f"- **{k}**: {v}\n"
            md += "\n"

    md += "---\n\n## 二、QA 测试结果\n\n"
    md += "| # | 问题 | 路径数 | 来源引用 | 回答长度 |\n"
    md += "|---|------|--------|----------|----------|\n"
    for i, qa in enumerate(r.get("qa_results", []), 1):
        src = "✓" if qa.get("has_sources") else "✗"
        md += f"| {i} | {qa['question'][:30]}... | {qa['path_count']} | {src} | {qa.get('answer_length', 0)} |\n"

    md += "\n---\n\n## 三、数据质量\n\n"
    dq = r.get("data_quality", {})
    md += f"### 关系数据库\n\n"
    md += f"- accidents: {dq.get('accidents_total', 0)} 行\n"
    md += f"- chemical_properties: {dq.get('chemicals_total', 0)} 行\n"
    md += f"- weather_records: {dq.get('weather_total', 0)} 行\n"
    md += f"- 日期范围: {dq.get('date_range', 'N/A')}\n\n"

    if "neo4j_node_types" in dq:
        md += "### 图数据库节点类型\n\n"
        md += "| 类型 | 数量 |\n|------|------|\n"
        for typ, cnt in dq["neo4j_node_types"].items():
            md += f"| {typ} | {cnt} |\n"

    md += "\n---\n\n## 四、E/R 图\n\n"
    md += r.get("er_diagram_mermaid", "")

    md += "\n---\n\n## 五、性能基准\n\n"
    md += "| 查询 | 耗时 |\n|------|------|\n"
    for b in r.get("performance", {}).get("neo4j_benchmarks", []):
        md += f"| {b['query']} | {b['time_ms']}ms |\n"

    md += "\n---\n\n*本报告由 scripts/run_evaluation.py 自动生成*\n"
    return md


# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("ChemSafe-KG 综合评估开始")

    run_sql_queries()
    run_qa_tests()
    run_data_quality()
    generate_er_diagram()
    run_performance_benchmark()

    # 保存 JSON
    Path(OUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"JSON 报告: {OUT_JSON}")

    # 生成 Markdown
    md = generate_markdown()
    Path(OUT_MD).write_text(md, encoding="utf-8")
    logger.info(f"Markdown 报告: {OUT_MD}")

    logger.info("\n评估完成")
