"""
数据库初始化脚本

运行此脚本创建关系数据库表结构和 Neo4j 图数据库 Schema。

使用方式:
    python scripts/init_db.py

TODO [完善]:
  1. 确保 .env 文件已配置
  2. 确保 Neo4j 服务已启动
  3. 根据需要调整表结构
"""
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")


def init_relational_db():
    """初始化关系数据库"""
    try:
        from config.database import init_relational_db as init_sql
        from src.storage.relational_db import AccidentRecord, ChemicalProperty, WeatherRecord

        init_sql()
        logger.info("✅ 关系数据库表结构初始化完成")
    except Exception as e:
        logger.error(f"❌ 关系数据库初始化失败: {e}")


def init_neo4j():
    """初始化 Neo4j 图数据库"""
    try:
        from src.storage.neo4j_client import Neo4jClient
        from src.storage.schema_manager import GraphSchema

        client = Neo4jClient()
        client.connect()

        statements = GraphSchema.create_index_constraints(client.graph)
        logger.info(f"✅ Neo4j 索引和约束已创建: {len(statements)} 条")
    except Exception as e:
        logger.warning(f"⚠️ Neo4j 初始化失败: {e}")
        logger.warning("请确保 Neo4j 服务已启动并在 .env 中正确配置。")


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("ChemSafe-KG 数据库初始化")
    logger.info("=" * 50)

    init_relational_db()
    init_neo4j()

    logger.info("数据库初始化完成。")
