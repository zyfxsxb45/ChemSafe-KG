"""
关系数据库操作模块

管理事故主表、化学品物性表、气象数据表等结构化数据的存取。
表结构已根据实际 PubChem API 和 LLM 抽取结果确定。
"""
import logging
from typing import Optional
import pandas as pd
from sqlalchemy import Table, MetaData, Column, String, Float, Date, Text, Integer
from config.database import engine, Base

logger = logging.getLogger(__name__)


# ─── ORM 模型定义 ──────────────────────────────────────────────────────────
class AccidentRecord(Base):
    """事故记录表 — 字段已根据实际 LLM 抽取结果确定"""
    __tablename__ = "accidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500))
    date = Column(Date)
    location = Column(String(200))
    industry = Column(String(200))
    summary = Column(Text)
    casualties = Column(String(100))
    source_url = Column(String(500))
    raw_text_path = Column(String(500))
    
    # 新增大模型提取的结构化字段
    root_cause = Column(Text)
    consequence = Column(Text)
    related_chemicals = Column(String(500))
    related_equipment = Column(String(500))


class ChemicalProperty(Base):
    """化学品物性表（数据源: PubChem via pubchempy）"""
    __tablename__ = "chemical_properties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # ── 基础标识 ──
    chemical_name = Column(String(200), unique=True, nullable=False, comment="中文名")
    english_name = Column(String(200), comment="英文名")
    cas_number = Column(String(50), comment="CAS号")
    iupac_name = Column(String(500), comment="IUPAC系统命名")
    # ── 基础物性 ──
    molecular_weight = Column(Float, comment="分子量 (g/mol)")
    # ── 安全相关物性（PubChem 不一定有值，需额外查询）──
    boiling_point = Column(Float, comment="沸点 (℃)")
    flash_point = Column(Float, comment="闪点 (℃)")
    upper_explosion_limit = Column(Float, comment="爆炸上限 (%)")
    lower_explosion_limit = Column(Float, comment="爆炸下限 (%)")
    vapor_pressure = Column(Float, comment="蒸气压 (mmHg)")
    autoignition_temp = Column(Float, comment="自燃温度 (℃)")
    toxicity_class = Column(String(100), comment="毒性分类")


class WeatherRecord(Base):
    """气象数据表"""
    __tablename__ = "weather_records"

    # TODO [完善]: 根据实际气象数据字段设计
    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(String(200))
    date = Column(Date)
    temperature_max = Column(Float)
    temperature_min = Column(Float)
    humidity = Column(Float)
    wind_speed = Column(Float)
    precipitation = Column(Float)
    weather_condition = Column(String(100))
