"""续抽取: 只处理未入库的文件"""
import os, sys, re, logging
from pathlib import Path
os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("continue")
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

from src.extraction.entity_extractor import EntityExtractor
from src.extraction.result_validator import ResultValidator
from src.storage.neo4j_client import Neo4jClient
from config.database import SessionLocal
from src.storage.relational_db import AccidentRecord

# 获取已处理标题
session = SessionLocal()
done_titles = set(r[0] for r in session.query(AccidentRecord.title).all())
session.close()
logger.info(f"已入库: {len(done_titles)} 条")

# 收集待处理文件
all_dirs = [
    Path("data/raw/wechat_reports"),
    Path("data/raw/accident_reports"),
]

pending = []
for d in all_dirs:
    if not d.exists():
        continue
    for f in sorted(d.glob("*.txt")):
        raw = f.read_text(encoding='utf-8')
        title_match = re.search(r"标题:\s*(.+)", raw)
        title = title_match.group(1).strip()[:500] if title_match else f.stem[:500]
        if title not in done_titles:
            pending.append(f)

logger.info(f"待处理: {len(pending)} 个文件")

if not pending:
    logger.info("全部已处理!")
    import sys; sys.exit(0)

neo4j = Neo4jClient()
neo4j.connect()
extractor = EntityExtractor()
validator = ResultValidator()

stats = {"success": 0, "failed": 0, "triples": 0, "mitigation": 0}
batch_triples, batch_maps = [], []

for i, fpath in enumerate(pending):
    raw = fpath.read_text(encoding='utf-8')
    text = re.split(r'={5,}', raw)[-1].strip() if '=====' in raw else raw
    if len(text) < 50:
        continue

    try:
        result = extractor.extract_from_text(text)
    except Exception:
        stats["failed"] += 1
        continue

    if not result or not validator.validate_structure(result):
        stats["failed"] += 1
        continue

    type_map = {}
    for item in result.get("event_chain", []):
        if "entity" in item and "type" in item:
            type_map[item["entity"]] = item["type"]

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

    # SQLite（含 date 提取，与 rebuild_all.py 保持一致）
    try:
        from datetime import datetime as dt_mod
        title_match = re.search(r"标题:\s*(.+)", raw)
        date_match = re.search(r"日期:\s*(.+)", raw)
        title = title_match.group(1).strip()[:500] if title_match else fpath.stem[:500]

        dt = None
        if date_match:
            date_str = date_match.group(1).strip()
            if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
                try:
                    dt = dt_mod.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

        # 判断来源
        if re.search(r"摘要:\s*", raw) or "wechat" in str(fpath):
            src = "微信"
        else:
            src = "mem"

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
        logger.info(f"  [{i}/{len(pending)}] {stats['success']}成功 mit={stats['mitigation']}")

    if len(batch_triples) >= 30:
        merged = {}
        for tm in batch_maps: merged.update(tm)
        neo4j.batch_create_triples(batch_triples, entity_type_map=merged, source_report=str(fpath))
        batch_triples, batch_maps = [], []

if batch_triples:
    merged = {}
    for tm in batch_maps: merged.update(tm)
    neo4j.batch_create_triples(batch_triples, entity_type_map=merged, source_report="final")

nodes = neo4j.get_entity_count()
rels = neo4j.get_relation_count()
logger.info(f"\n完成: {stats['success']}成功/{stats['failed']}失败, {stats['triples']}条")
logger.info(f"Mitigation出现在 {stats['mitigation']} 篇")
logger.info(f"Neo4j: {nodes} nodes, {rels} rels")

# Mitigation count
r = neo4j.graph.run("MATCH (n:Mitigation) RETURN count(n) as c").data()
logger.info(f"Mitigation总计: {r[0]['c']}")
