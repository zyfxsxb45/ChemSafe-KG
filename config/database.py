"""
数据库连接配置与 Session 管理

封装 SQLAlchemy 引擎和 Neo4j 驱动的连接创建逻辑。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import db as db_config

# ─── SQLAlchemy 引擎 ─────────────────────────────────────────────────────────
engine = create_engine(db_config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db_session():
    """获取关系数据库会话 (上下文管理器用法)"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_relational_db():
    """初始化关系数据库表结构"""
    Base.metadata.create_all(bind=engine)
