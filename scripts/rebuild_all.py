"""
ChemSafe-KG 全量重建脚本 v0.7 (最终版)

流程:
  1. 清空 Neo4j + SQLite accidents 表
  2. 爬取 mem.gov.cn 全部月度汇编（不限数量）
  3. 预处理微信公众号事故文章
  4. LLM 批量抽取全部数据（含优化后的 Mitigation Prompt）
  5. 化学品物性充实 + 统一融合视图
  6. QA 验证
  7. 统计报告

用法:
  python scripts/rebuild_all.py

预计耗时: 30-60 分钟（取决于网速和 DeepSeek API 响应速度）
"""
import os, sys, re, json, time, logging, shutil
from pathlib import Path
from datetime import datetime
from collections import Counter

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("rebuild")

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("jieba").setLevel(logging.WARNING)


# ═══════════════════════════════════════════════════════════════════
#  第零步: 清空
# ═══════════════════════════════════════════════════════════════════
def step_clear():
    """清空 Neo4j 和 SQLite accidents 表"""
    logger.info("=" * 60)
    logger.info("  [0/6] 清空数据库")
    logger.info("=" * 60)

    # Neo4j
    from src.storage.neo4j_client import Neo4jClient
    from src.storage.schema_manager import GraphSchema
    neo4j = Neo4jClient()
    neo4j.connect()
    if neo4j.graph:
        before = neo4j.get_entity_count()
        neo4j.clear_all()
        logger.info(f"  Neo4j: {before} 节点已清空")
        GraphSchema.create_index_constraints(neo4j.graph)
        logger.info(f"  Neo4j: 索引/约束已重建")

    # SQLite
    import sqlite3
    conn = sqlite3.connect("data/processed/chemsafe.db")
    before = conn.execute("SELECT count(*) FROM accidents").fetchone()[0]
    conn.execute("DELETE FROM accidents")
    conn.execute("DELETE FROM sqlite_sequence WHERE name='accidents'")
    conn.commit()
    conn.close()
    logger.info(f"  SQLite accidents: {before} 行已清空")

    # 清空旧报告文件
    for d in [Path("data/raw/accident_reports"), Path("data/raw/wechat_reports")]:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    logger.info(f"  旧报告文件已清空")


# ═══════════════════════════════════════════════════════════════════
#  第一步: 爬虫采集
# ═══════════════════════════════════════════════════════════════════
def step_crawl():
    """爬取 mem.gov.cn 全部事故（不限数量）"""
    logger.info("=" * 60)
    logger.info("  [1/6] 爬虫采集 (mem.gov.cn, 不限量)")
    logger.info("=" * 60)

    from src.acquisition.report_crawler import ReportCrawler
    c = ReportCrawler()
    c.run(max_reports=9999)  # 不设上限

    txt_files = sorted(Path("data/raw/accident_reports").glob("*.txt"))
    logger.info(f"  采集完成: {len(txt_files)} 份事故报告")
    return len(txt_files)


# ═══════════════════════════════════════════════════════════════════
#  第二步: 微信文章预处理
# ═══════════════════════════════════════════════════════════════════
def step_wechat_preprocess():
    """预处理微信公众号文章"""
    logger.info("=" * 60)
    logger.info("  [2/6] 微信文章预处理")
    logger.info("=" * 60)

    wechat_json = Path("../newdata.json")
    if not wechat_json.exists():
        logger.warning("  newdata.json 不存在，跳过")
        return 0

    with open(wechat_json, encoding='utf-8') as f:
        data = json.load(f)

    # 筛选事故详情类
    accidents = []
    for a in data:
        t = a.get('title', '')
        c = str(a.get('content', ''))
        if len(c) < 300:
            continue
        if not re.search(r'事故|爆炸|泄漏|中毒|火灾|伤亡|爆燃|闪爆', t):
            continue
        if not re.search(r'原因|分析|调查|经过|处置|施救|救援|教训|警示|防范|措施|整改|直接原因', c):
            continue
        accidents.append(a)

    logger.info(f"  筛选: {len(accidents)}/{len(data)} 篇事故详情")

    # 清洗并保存
    output_dir = Path("data/raw/wechat_reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = 0

    for a in accidents:
        title = a.get('title', 'untitled')
        raw = str(a.get('content', ''))
        digest = a.get('digest', '')

        # 清洗微信噪声
        text = raw
        for pattern in [
            r'点击上方蓝字.*?关注.*?\n?', r'点击.*?关注.*?公众号.*?\n?',
            r'微信号[：:]\s*\S+\s*\n?', r'长按.*?识别.*?关注.*?\n?',
            r'编辑[：:].*?\n', r'来源[：:].*?\n', r'责编[：:].*?\n', r'审核[：:].*?\n',
            r'\[图片\]', r'\(图片.*?\)', r'二维码', r'阅读\s*\d+', r'点赞\s*\d+',
            r'<[^>]+>', r'&nbsp;', r'&amp;', r'&lt;', r'&gt;',
        ]:
            text = re.sub(pattern, '', text, flags=re.I if pattern.startswith(r'<') else 0)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        if len(text) < 100:
            continue

        full = f"标题: {title}\n"
        if digest and len(digest) > 10:
            full += f"摘要: {digest}\n"
        full += f"{'='*50}\n{text}"

        safe_title = re.sub(r'[\\/:*?"<>|]', '', title)[:60]
        (output_dir / f"{safe_title}.txt").write_text(full, encoding='utf-8')
        saved += 1

    logger.info(f"  保存: {saved} 篇")
    return saved


# ═══════════════════════════════════════════════════════════════════
#  第三步: LLM 批量抽取
# ═══════════════════════════════════════════════════════════════════
def _parse_meta(raw_text: str, fpath: Path):
    """
    从报告文件 frontmatter 提取元信息。

    mem.gov.cn 格式:
        标题: XXX\n来源: mem.gov.cn\n日期: 2020-05-07\n月度汇编: XXX\n=====
    微信格式:
        标题: XXX\n摘要: XXX\n=====

    Returns: (title, date, source_label)
    """
    from datetime import datetime

    title_match = re.search(r"标题:\s*(.+)", raw_text)
    date_match = re.search(r"日期:\s*(.+)", raw_text)
    title = title_match.group(1).strip()[:500] if title_match else fpath.stem[:500]

    dt = None
    if date_match:
        date_str = date_match.group(1).strip()
        if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

    # 判断来源: 微信文章有"摘要:"字段，mem 报告有"来源:"或"月度汇编:"字段
    if re.search(r"摘要:\s*", raw_text) or "wechat" in str(fpath):
        src = "微信"
    elif re.search(r"月度汇编:\s*", raw_text) or re.search(r"来源:\s*mem", raw_text):
        src = "mem"
    else:
        src = "mem"

    return title, dt, src


def _extract_from_dir(input_dir: str, label: str):
    """从目录批量抽取 → Neo4j + SQLite 双写（含 Accident 聚合节点）"""
    from src.extraction.entity_extractor import EntityExtractor
    from src.extraction.result_validator import ResultValidator
    from src.storage.neo4j_client import Neo4jClient
    from config.database import SessionLocal
    from src.storage.relational_db import AccidentRecord

    neo4j = Neo4jClient()
    neo4j.connect()
    extractor = EntityExtractor()
    validator = ResultValidator()

    files = sorted(Path(input_dir).glob("*.txt"))
    if not files:
        logger.warning(f"  {label}: 无文件")
        return {"total": 0, "success": 0, "failed": 0, "triples": 0, "mitigation": 0}

    logger.info(f"  {label}: {len(files)} 个文件")

    stats = {"total": 0, "success": 0, "failed": 0, "triples": 0, "mitigation": 0}
    batch_triples, batch_maps = [], []
    file_accidents = []  # 收集事故元信息，用于创建 Accident 节点

    for i, fpath in enumerate(files):
        raw = fpath.read_text(encoding='utf-8')
        text = re.split(r'={5,}', raw)[-1].strip() if '=====' in raw else raw
        if len(text) < 50:
            continue

        stats["total"] += 1
        try:
            result = extractor.extract_from_text(text)
        except Exception:
            stats["failed"] += 1
            continue

        if not result or not validator.validate_structure(result):
            stats["failed"] += 1
            continue

        type_map = _extract_type_map(result)
        triples = extractor.convert_to_triples(result)
        if not triples:
            stats["failed"] += 1
            continue

        batch_triples.extend(triples)
        batch_maps.append(type_map)
        stats["success"] += 1
        stats["triples"] += len(triples)
        if "Mitigation" in set(type_map.values()):
            stats["mitigation"] += 1

        # 记录事故元信息（用于后续创建 Accident 聚合节点）
        title, dt, src = _parse_meta(raw, fpath)
        file_accidents.append({
            "title": title,
            "date": str(dt) if dt else "",
            "source_url": f"{src}:{fpath.name}",
            "root_cause": result.get("root_cause", ""),
            "consequence": result.get("consequence", ""),
            "entity_names": list(type_map.keys()),
        })

        # SQLite 写入
        try:
            session = SessionLocal()
            existing = session.query(AccidentRecord).filter_by(title=title).first()
            if not existing:
                chems = ",".join(n for n, t in type_map.items() if t == "Material")
                equips = ",".join(n for n, t in type_map.items() if t == "Equipment")
                session.add(AccidentRecord(
                    title=title, date=dt, summary=text[:500],
                    source_url=f"{src}:{fpath.name}",
                    root_cause=result.get("root_cause", ""),
                    consequence=result.get("consequence", ""),
                    related_chemicals=chems, related_equipment=equips,
                ))
                session.commit()
            session.close()
        except Exception:
            pass

        if i % 20 == 0 and i > 0:
            logger.info(f"    [{i}/{len(files)}] {stats['success']}成功 mit={stats['mitigation']}")

        # 每 30 条三元组批量写入 Neo4j
        if len(batch_triples) >= 30:
            _flush_neo4j(neo4j, batch_triples, batch_maps, str(fpath))
            batch_triples, batch_maps = [], []

    if batch_triples:
        _flush_neo4j(neo4j, batch_triples, batch_maps, "final")

    # 创建 Accident 聚合节点，链接所有实体
    if file_accidents:
        _create_accident_nodes(neo4j, file_accidents)

    logger.info(f"    {label}: {stats['success']}成功/{stats['failed']}失败, {stats['triples']}条, Mitigation出现在{stats['mitigation']}篇")
    return stats


def _extract_type_map(result):
    m = {}
    for item in result.get("event_chain", []):
        if "entity" in item and "type" in item:
            m[item["entity"]] = item["type"]
    return m


def _flush_neo4j(neo4j, triples, maps, src):
    merged = {}
    for tm in maps:
        merged.update(tm)
    neo4j.batch_create_triples(triples, entity_type_map=merged, source_report=src)


def _create_accident_nodes(neo4j, file_accidents: list):
    """
    为每个事故文件创建 Accident 聚合节点，
    并将该事故中所有实体通过 belongs_to 关系链接到 Accident 节点。
    """
    if neo4j.graph is None:
        return

    created = 0
    linked = 0

    for acc in file_accidents:
        entity_names = acc.get("entity_names", [])
        if not entity_names:
            continue

        title = acc["title"]
        source_url = acc.get("source_url", "")
        date_str = acc.get("date", "")

        # MERGE Accident 节点（按 title 去重）
        neo4j.graph.run(
            "MERGE (a:Accident {title: $title}) "
            "SET a.source_url = $source_url, a.date = $date, "
            "a.root_cause = $root_cause, a.consequence = $consequence",
            title=title,
            source_url=source_url,
            date=date_str,
            root_cause=acc.get("root_cause", ""),
            consequence=acc.get("consequence", ""),
        )
        created += 1

        # 链接实体 → Accident（只链接在该事故 event_chain 中出现的实体）
        for ename in entity_names:
            if not ename or len(ename) < 2:
                continue
            try:
                neo4j.graph.run(
                    "MATCH (a:Accident {title: $title}) "
                    "MATCH (e {name: $ename}) "
                    "WHERE size(labels(e)) > 0 "
                    "MERGE (e)-[:belongs_to]->(a)",
                    title=title, ename=ename,
                )
                linked += 1
            except Exception:
                pass

    logger.info(f"    Accident节点: {created} 个创建, {linked} 个实体关联")


def step_extract():
    """LLM批量抽取: 先微信, 后爬虫"""
    logger.info("=" * 60)
    logger.info("  [3/6] LLM 知识抽取")
    logger.info("=" * 60)

    # 先微信（质量更高，Mitigation更丰富）
    wx_stats = _extract_from_dir("data/raw/wechat_reports", "微信")
    # 再 mem（量大）
    crawl_stats = _extract_from_dir("data/raw/accident_reports", "mem")

    combined = {
        "total": wx_stats["total"] + crawl_stats["total"],
        "success": wx_stats["success"] + crawl_stats["success"],
        "failed": wx_stats["failed"] + crawl_stats["failed"],
        "triples": wx_stats["triples"] + crawl_stats["triples"],
        "mitigation_articles": wx_stats["mitigation"] + crawl_stats["mitigation"],
    }
    logger.info(f"  合计: {combined['success']}/{combined['total']}成功, {combined['triples']}条三元组")
    return combined


# ═══════════════════════════════════════════════════════════════════
#  第四步: 充实
# ═══════════════════════════════════════════════════════════════════
def step_enrich():
    """化学品物性 + 统一视图"""
    logger.info("=" * 60)
    logger.info("  [4/6] 数据充实")
    logger.info("=" * 60)

    csv = Path("data/external/chemical_properties.csv")
    if not csv.exists():
        logger.warning("  chemical_properties.csv 不存在，跳过")
        return

    import pandas as pd
    chem_df = pd.read_csv(csv)

    # 写入 SQLite chemical_properties
    import sqlite3
    conn = sqlite3.connect("data/processed/chemsafe.db")
    for _, row in chem_df.iterrows():
        try:
            conn.execute("""
                INSERT OR IGNORE INTO chemical_properties
                (chemical_name, english_name, cas_number, iupac_name, molecular_weight)
                VALUES (?, ?, ?, ?, ?)
            """, (row.get('chemical_name',''), row.get('english_name',''),
                  row.get('cas_number',''), row.get('iupac_name',''),
                  row.get('molecular_weight')))
        except Exception:
            pass
    conn.commit()

    ch_count = conn.execute("SELECT count(*) FROM chemical_properties").fetchone()[0]
    acc_count = conn.execute("SELECT count(*) FROM accidents").fetchone()[0]
    conn.close()

    logger.info(f"  chemical_properties: {ch_count} 种")
    logger.info(f"  accidents: {acc_count} 条")

    # 统一融合视图
    try:
        from config.database import engine
        accidents_df = pd.read_sql("SELECT * FROM accidents", engine)
        from src.preprocessing.data_merger import DataMerger
        merger = DataMerger()
        unified = merger.build_unified_view(accidents_df, chem_df)
        unified.to_csv("data/processed/unified_view.csv", index=False)
        logger.info(f"  统一视图: {len(unified)} 行 x {len(unified.columns)} 列")
    except Exception as e:
        logger.warning(f"  统一视图失败: {e}")


# ═══════════════════════════════════════════════════════════════════
#  第五步: 验证
# ═══════════════════════════════════════════════════════════════════
def step_verify():
    """QA 验证 + 统计"""
    logger.info("=" * 60)
    logger.info("  [5/6] 验证")
    logger.info("=" * 60)

    from src.storage.neo4j_client import Neo4jClient
    neo4j = Neo4jClient()
    neo4j.connect()

    if neo4j.graph:
        r = neo4j.graph.run("""
            MATCH (n) WHERE size(labels(n))>0
            RETURN labels(n)[0] as l, count(*) as c ORDER BY c DESC
        """).data()
        logger.info("  Neo4j 最终状态:")
        for row in r:
            logger.info(f"    {row['l']:25s}: {row['c']:5d}")
        total = sum(row['c'] for row in r)
        rels = neo4j.graph.run("MATCH ()-[r]->() RETURN count(r) as c").data()[0]['c']
        acc_count = neo4j.graph.run("MATCH (a:Accident) RETURN count(a) as c").data()[0]['c']
        logger.info(f"    {'Total':25s}: {total:5d} nodes, {rels} rels, {acc_count} Accident")

    import sqlite3
    conn = sqlite3.connect("data/processed/chemsafe.db")
    acc = conn.execute("SELECT count(*) FROM accidents").fetchone()[0]
    mit = conn.execute("SELECT count(*) FROM accidents WHERE root_cause IS NOT NULL AND root_cause!=''").fetchone()[0]
    conn.close()
    logger.info(f"  SQLite: {acc} accidents, {mit} with root_cause")


# ═══════════════════════════════════════════════════════════════════
#  第六步: 报告
# ═══════════════════════════════════════════════════════════════════
def step_report():
    """生成最终统计报告"""
    from src.storage.neo4j_client import Neo4jClient
    neo4j = Neo4jClient()
    neo4j.connect()
    import sqlite3

    report = {
        "timestamp": datetime.now().isoformat(),
        "neo4j": {},
        "sqlite": {},
    }

    if neo4j.graph:
        r = neo4j.graph.run("MATCH (n) RETURN labels(n)[0] as l, count(*) as c ORDER BY c DESC").data()
        report["neo4j"]["node_types"] = {row['l']: row['c'] for row in r}
        report["neo4j"]["total_nodes"] = sum(row['c'] for row in r)
        report["neo4j"]["total_rels"] = neo4j.graph.run("MATCH ()-[r]->() RETURN count(r) as c").data()[0]['c']

        # Mitigation 详情
        r = neo4j.graph.run("MATCH (n:Mitigation) RETURN n.name as name").data()
        report["neo4j"]["mitigation_nodes"] = [row['name'] for row in r]

    conn = sqlite3.connect("data/processed/chemsafe.db")
    report["sqlite"]["accidents"] = conn.execute("SELECT count(*) FROM accidents").fetchone()[0]
    report["sqlite"]["chemicals"] = conn.execute("SELECT count(*) FROM chemical_properties").fetchone()[0]
    conn.close()

    Path("data/processed/final_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"  报告: data/processed/final_report.json")


# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  ChemSafe-KG 全量重建 v0.7")
    logger.info("=" * 60)

    t0 = time.time()

    step_clear()
    crawl_count = step_crawl()
    wechat_count = step_wechat_preprocess()
    extract_stats = step_extract()
    step_enrich()
    step_verify()
    step_report()

    elapsed = time.time() - t0
    logger.info(f"\n{'='*60}")
    logger.info(f"  全量重建完成! 耗时 {elapsed/60:.0f} 分钟")
    logger.info(f"  爬虫: {crawl_count} 份 | 微信: {wechat_count} 篇")
    logger.info(f"  抽取: {extract_stats['success']}/{extract_stats['total']} 成功")
    logger.info(f"  三元组: {extract_stats['triples']} 条")
    logger.info(f"{'='*60}")
