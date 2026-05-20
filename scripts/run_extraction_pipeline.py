"""
批量知识抽取流水线运行脚本

从爬虫抓取的 .txt 事故报告中，调用 LLM 抽取实体关系，
构建知识图谱并写入 Neo4j。

运行方式:
    python scripts/run_extraction_pipeline.py --input data/raw/accident_reports

前置条件:
    1. .env 中已配置 LLM_API_KEY (DeepSeek)
    2. Neo4j 服务已启动 (localhost:7687)
    3. 已运行 python scripts/init_db.py 初始化 Schema
"""
import re
import argparse
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("extraction_pipeline")

# 压低 LLM SDK 的冗长日志
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Windows GBK 兼容
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def extract_entity_type_map(extraction_result: dict) -> dict:
    """
    从 LLM 抽取结果中提取 {实体名: 实体类型} 映射。

    extraction_result 的 event_chain 包含交替的实体定义和关系。
    """
    type_map = {}
    for item in extraction_result.get("event_chain", []):
        if "entity" in item and "type" in item:
            type_map[item["entity"]] = item["type"]
        if "relation" in item and "target" in item:
            target = item["target"]
            if target not in type_map and "type" in item:
                type_map[target] = item.get("type", "Abnormal_Condition")
    return type_map


def _save_to_relational_db(file_path: Path, raw_text: str, accident_text: str):
    """将事故基础信息提取并存入关系型数据库 (SQLite)"""
    from config.database import SessionLocal
    from src.storage.relational_db import AccidentRecord
    from datetime import datetime

    title_match = re.search(r"标题:\s*(.+)", raw_text)
    date_match = re.search(r"日期:\s*(.+)", raw_text)
    source_match = re.search(r"来源:\s*(.+)", raw_text)

    title = title_match.group(1).strip() if title_match else file_path.stem
    date_str = date_match.group(1).strip() if date_match else ""
    source = source_match.group(1).strip() if source_match else ""

    dt = None
    if date_str and re.match(r"\d{4}-\d{2}-\d{2}", date_str):
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    session = SessionLocal()
    try:
        existing = session.query(AccidentRecord).filter_by(title=title).first()
        if not existing:
            record = AccidentRecord(
                title=title,
                date=dt,
                summary=accident_text[:500] + "..." if len(accident_text) > 500 else accident_text,
                source_url=source,
                raw_text_path=str(file_path)
            )
            session.add(record)
            session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"关系数据库写入失败: {e}")
    finally:
        session.close()


def strip_header(text: str) -> str:
    """
    去除爬虫文件头部的元信息 (标题/来源/日期/月度汇编/=====)，
    只保留事故描述文本。
    """
    # 找到 ==== 分隔线后的正文
    match = re.split(r'={5,}\s*', text)
    if len(match) >= 2:
        return match[-1].strip()
    return text.strip()


def run(input_dir: str, batch_size: int = 5, skip_existing: bool = True):
    """
    运行批量知识抽取流水线。

    流程:
      1. 扫描输入目录中的所有 .txt 文件
      2. 逐个读取、清洗、调用 LLM 抽取
      3. 每 batch_size 条批量写入 Neo4j
      4. 输出统计摘要

    Args:
        input_dir: 爬虫抓取的事故报告目录
        batch_size: 每多少条写入一次 Neo4j (减少连接开销)
        skip_existing: 是否跳过已经处理过的文件 (基于缓存记录)
    """
    logger.info("=" * 60)
    logger.info("  ChemSafe-KG 批量知识抽取流水线")
    logger.info("=" * 60)

    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error(f"输入目录不存在: {input_path}")
        logger.error("请先运行爬虫: ReportCrawler().run(max_reports=50)")
        return

    # ── 获取待处理文件列表 ──
    all_files = sorted(input_path.glob("*.txt"))
    if not all_files:
        logger.error(f"输入目录中没有 .txt 文件: {input_path}")
        return

    logger.info(f"发现 {len(all_files)} 个事故报告文件")

    # ── 初始化模块 ──
    logger.info("\n[初始化] 加载抽取引擎和 Neo4j 连接...")
    from src.extraction.entity_extractor import EntityExtractor
    from src.extraction.result_validator import ResultValidator
    from src.storage.neo4j_client import Neo4jClient
    from src.storage.schema_manager import GraphSchema

    extractor = EntityExtractor()
    validator = ResultValidator()
    neo4j = Neo4jClient()
    neo4j.connect()

    if neo4j.graph is None:
        logger.error("Neo4j 连接失败，请检查服务是否运行")
        return

    # 确保 Schema 已创建
    GraphSchema.create_index_constraints(neo4j.graph)
    logger.info("  模块初始化完成")

    # 查看入库前状态
    before_nodes = neo4j.get_entity_count()
    before_rels = neo4j.get_relation_count()
    logger.info(f"  入库前 Neo4j: {before_nodes} 节点, {before_rels} 关系")

    # ── 逐条抽取 ──
    logger.info(f"\n[抽取] 开始 LLM 知识抽取 (共 {len(all_files)} 条)...")

    stats = {
        "total": len(all_files),
        "success": 0,
        "skipped": 0,
        "failed": 0,
        "total_triples": 0,
    }

    pending_triples = []
    pending_type_maps = []
    pending_sources = []

    for idx, file_path in enumerate(all_files, 1):
        # 读取并清洗
        raw_text = file_path.read_text(encoding="utf-8")
        accident_text = strip_header(raw_text)

        if not accident_text or len(accident_text) < 20:
            logger.warning(f"  [{idx}/{stats['total']}] 跳过 (文本过短): {file_path.name}")
            stats["skipped"] += 1
            continue

        # 日志: 简短文件信息
        title_line = re.search(r"标题: (.+)", raw_text)
        title = title_line.group(1) if title_line else file_path.stem
        logger.info(f"  [{idx}/{stats['total']}] {title[:45]:45s} ({len(accident_text)}字符)")

        # 写入关系型数据库 (SQLite)
        _save_to_relational_db(file_path, raw_text, accident_text)

        # 调用 LLM 抽取
        try:
            result = extractor.extract_from_text(accident_text)
        except Exception as e:
            logger.warning(f"    → LLM 调用失败: {e}")
            stats["failed"] += 1
            continue

        # 验证结果
        if not result or not validator.validate_structure(result):
            logger.warning(f"    → 抽取结果无效 (空或结构不完整)")
            stats["failed"] += 1
            continue

        # 转换为三元组
        type_map = extract_entity_type_map(result)
        triples = extractor.convert_to_triples(result)

        if not triples:
            logger.warning(f"    → 未提取到三元组")
            stats["failed"] += 1
            continue

        pending_triples.extend(triples)
        pending_type_maps.append(type_map)
        pending_sources.append(file_path.name)
        stats["success"] += 1
        stats["total_triples"] += len(triples)

        entities_found = set(type_map.values())
        logger.info(f"    → {len(triples)} 三元组, 实体类型: {entities_found}")

        # 每 batch_size 条写入一次 Neo4j
        if len(pending_sources) >= batch_size:
            _flush_to_neo4j(neo4j, pending_triples, pending_type_maps, pending_sources)
            pending_triples, pending_type_maps, pending_sources = [], [], []

    # 写入最后一批
    if pending_triples:
        _flush_to_neo4j(neo4j, pending_triples, pending_type_maps, pending_sources)

    # ── 统计摘要 ──
    after_nodes = neo4j.get_entity_count()
    after_rels = neo4j.get_relation_count()

    logger.info("\n" + "=" * 60)
    logger.info("  抽取完成!")
    logger.info(f"  成功: {stats['success']} | 跳过: {stats['skipped']} | 失败: {stats['failed']}")
    logger.info(f"  共抽取 {stats['total_triples']} 条三元组")
    logger.info(f"  Neo4j: {before_nodes}→{after_nodes} 节点 (+{after_nodes-before_nodes})")
    logger.info(f"         {before_rels}→{after_rels} 关系 (+{after_rels-before_rels})")

    entities = neo4j.get_all_entity_names()
    logger.info(f"  实体示例 (前 10): {entities[:10]}")

    logger.info("\n启动问答界面:")
    logger.info("  streamlit run app.py")
    logger.info("=" * 60)


def _flush_to_neo4j(neo4j, triples, type_maps, sources):
    """将一批三元组写入 Neo4j"""
    merged_type_map = {}
    for tm in type_maps:
        merged_type_map.update(tm)

    source_label = f"batch_{len(sources)}files"
    neo4j.batch_create_triples(triples, entity_type_map=merged_type_map, source_report=source_label)
    logger.info(f"  [写入] {len(triples)} 条三元组入库 (来自 {len(sources)} 份报告)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ChemSafe-KG 批量知识抽取流水线"
    )
    parser.add_argument(
        "--input",
        default="data/raw/accident_reports",
        help="爬虫抓取的事故报告目录 (默认: data/raw/accident_reports)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="每 N 条写入一次 Neo4j (默认: 5)",
    )
    args = parser.parse_args()

    run(input_dir=args.input, batch_size=args.batch_size)
