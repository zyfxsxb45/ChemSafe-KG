"""
种子数据插入脚本

向数据库中插入少量示例/测试数据，用于开发阶段的调试和验证。

使用方式:
    python scripts/seed_data.py
"""
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_data")


# ─── 示例种子数据 ─────────────────────────────────────────────────────────
SEED_ACCIDENTS = [
    {
        "title": "某化工厂丙烯腈储罐爆炸事故",
        "date": date(2023, 5, 7),
        "location": "江苏省",
        "industry": "化工",
        "summary": "丙烯腈储罐区因冷却水循环泵故障，导致储罐温度持续上升，引发丙烯腈自聚放热反应，最终储罐超压破裂导致爆炸。",
        "source_url": "",
    },
    {
        "title": "某石化企业苯泄漏中毒事故",
        "date": date(2022, 8, 15),
        "location": "山东省",
        "industry": "石化",
        "summary": "苯储罐出口法兰密封失效，导致苯大量泄漏，造成3人中毒。",
        "source_url": "",
    },
]


def seed_relational_db():
    """向关系数据库插入种子数据"""
    try:
        from config.database import SessionLocal, init_relational_db
        from src.storage.relational_db import AccidentRecord

        init_relational_db()
        session = SessionLocal()

        for data in SEED_ACCIDENTS:
            record = AccidentRecord(**data)
            session.add(record)

        session.commit()
        session.close()
        logger.info(f"已插入 {len(SEED_ACCIDENTS)} 条事故记录")
    except Exception as e:
        logger.error(f"关系数据库插入失败: {e}")


def seed_neo4j():
    """使用 LLM 抽取种子数据并写入 Neo4j"""
    try:
        from src.extraction.entity_extractor import EntityExtractor
        from src.storage.neo4j_client import Neo4jClient
        from scripts.run_demo_pipeline import extract_entity_type_map

        client = Neo4jClient()
        client.connect()

        extractor = EntityExtractor()

        for accident in SEED_ACCIDENTS:
            result = extractor.extract_from_text(accident["summary"])
            if not result:
                logger.warning(f"抽取失败: {accident['title']}")
                continue

            type_map = extract_entity_type_map(result)
            triples = extractor.convert_to_triples(result)
            client.batch_create_triples(triples, entity_type_map=type_map)
            logger.info(f"已插入: {accident['title']} ({len(triples)} 条)")

        logger.info(f"Neo4j 种子数据完成: {client.get_entity_count()} 节点")
    except Exception as e:
        logger.warning(f"Neo4j 种子数据插入失败: {e}")


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("ChemSafe-KG 种子数据插入")
    logger.info("=" * 50)

    seed_relational_db()
    seed_neo4j()

    logger.info("种子数据插入完成。")
