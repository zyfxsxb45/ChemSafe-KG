"""
关系数据库操作模块

管理事故主表、化学品物性表、气象数据表等结构化数据的存取。

TODO [数据接入]: 关系数据库表结构需要根据实际数据建模确定
"""
import logging
from typing import Optional
import pandas as pd
from sqlalchemy import Table, MetaData, Column, String, Float, Date, Text, Integer
from config.database import engine, Base

logger = logging.getLogger(__name__)


# ─── ORM 模型定义 ──────────────────────────────────────────────────────────
class AccidentRecord(Base):
    """事故记录表"""
    __tablename__ = "accidents"

    # TODO [完善]: 根据实际数据设计字段
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
    """化学品物性表"""
    __tablename__ = "chemical_properties"

    # TODO [完善]: 根据实际 API 返回字段设计
    id = Column(Integer, primary_key=True, autoincrement=True)
    chemical_name = Column(String(200), unique=True)
    cas_number = Column(String(50))
    boiling_point = Column(Float)
    flash_point = Column(Float)
    upper_explosion_limit = Column(Float)
    lower_explosion_limit = Column(Float)
    vapor_pressure = Column(Float)
    toxicity_class = Column(String(100))


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
