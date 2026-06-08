"""
ChemSafe-KG 全局配置模块

集中管理所有配置项，优先从 .env 文件读取，提供合理的默认值。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 加载 .env 文件
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.local", override=True)


# ─── LLM API 配置 ───────────────────────────────────────────────────────────
class LLMConfig:
    API_KEY: str = os.getenv("LLM_API_KEY", "")
    BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    MODEL: str = os.getenv("LLM_MODEL", "deepseek-chat")
    MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "8192"))
    TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))  # 低温度保证抽取一致性


# ─── Neo4j 图数据库配置 ──────────────────────────────────────────────────────
class Neo4jConfig:
    URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USER: str = os.getenv("NEO4J_USER", "neo4j")
    PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")


# ─── 关系数据库配置 ─────────────────────────────────────────────────────────
class DBConfig:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{PROJECT_ROOT / 'data' / 'processed' / 'chemsafe.db'}",
    )


# ─── 数据路径 ───────────────────────────────────────────────────────────────
class DataPaths:
    RAW_DIR: Path = PROJECT_ROOT / "data" / "raw"
    PROCESSED_DIR: Path = PROJECT_ROOT / "data" / "processed"
    ONTOLOGY_DIR: Path = PROJECT_ROOT / "data" / "external" / "ontology"
    REPORTS_DIR: Path = RAW_DIR / "accident_reports"
    CHEMICAL_DIR: Path = RAW_DIR / "chemical_properties"
    WEATHER_DIR: Path = RAW_DIR / "weather_data"


# ─── 爬虫配置 ───────────────────────────────────────────────────────────────
class CrawlerConfig:
    DELAY: float = float(os.getenv("CRAWLER_DELAY", "3.0"))
    USER_AGENT: str = os.getenv(
        "CRAWLER_USER_AGENT",
        "Mozilla/5.0 ChemSafe-KG/1.0 (Academic Project)",
    )
    TIMEOUT: int = 30


# ─── 知识抽取配置 ──────────────────────────────────────────────────────────
class ExtractionConfig:
    ENTITY_TYPES = [
        "Equipment",         # 设备
        "Material",          # 物料/化学品
        "Abnormal_Condition",  # 异常状态
        "Consequence",       # 事故后果
        "Mitigation",        # 应急措施
    ]
    RELATION_TYPES = [
        "leads_to",          # 导致
        "involves",          # 涉及
        "mitigated_by",      # 被缓解
        "occurs_at",         # 发生于
        "has_property",      # 具有属性
    ]
    MAX_CHAIN_LENGTH: int = 8  # 单条因果链最大步数


# ─── 全局单例访问 ──────────────────────────────────────────────────────────
llm = LLMConfig()
neo4j = Neo4jConfig()
db = DBConfig()
paths = DataPaths()
crawler = CrawlerConfig()
extraction = ExtractionConfig()
