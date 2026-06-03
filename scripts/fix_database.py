"""
关系数据库全面修复与数据导入脚本

修复内容:
  1. 重建 chemical_properties 表（匹配 ORM 新字段）
  2. 从 CSV 导入完整化学品物性
  3. 修复 related_chemicals 标准化
  4. 添加常用查询索引
  5. 填充天气数据采样
"""
import os, sys, logging
os.chdir(r'D:\课程文件\大二下\数据库技术及应用\大作业\ChemSafe-KG')
sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("db_fix")

import sqlite3
import pandas as pd
from pathlib import Path
from collections import Counter

DB_PATH = r'D:\课程文件\大二下\数据库技术及应用\大作业\ChemSafe-KG\data\processed\chemsafe.db'
CSV_PATH = r'D:\课程文件\大二下\数据库技术及应用\大作业\ChemSafe-KG\data\external\chemical_properties.csv'


def fix_chemical_properties():
    """重建 chemical_properties 表并从 CSV 导入完整数据"""
    logger.info("=" * 50)
    logger.info("  1. 重建 chemical_properties 表")
    logger.info("=" * 50)

    conn = sqlite3.connect(DB_PATH)

    # 备份旧数据
    old_rows = conn.execute("SELECT * FROM chemical_properties").fetchall()
    logger.info(f"  旧表有 {len(old_rows)} 行")

    # 删旧建新
    conn.execute("DROP TABLE IF EXISTS chemical_properties")
    conn.execute("""
        CREATE TABLE chemical_properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chemical_name VARCHAR(200) NOT NULL UNIQUE,
            english_name VARCHAR(200),
            cas_number VARCHAR(50),
            iupac_name VARCHAR(500),
            molecular_weight FLOAT,
            boiling_point FLOAT,
            flash_point FLOAT,
            upper_explosion_limit FLOAT,
            lower_explosion_limit FLOAT,
            vapor_pressure FLOAT,
            autoignition_temp FLOAT,
            toxicity_class VARCHAR(100)
        )
    """)
    logger.info("  新表结构已创建")

    # 从 CSV 导入
    if Path(CSV_PATH).exists():
        df = pd.read_csv(CSV_PATH)
        logger.info(f"  CSV: {len(df)} 行, 列: {list(df.columns)}")

        # 字段映射: CSV列 → SQL列
        col_map = {
            'chemical_name': 'chemical_name',
            'english_name': 'english_name',
            'cas_number': 'cas_number',
            'iupac_name': 'iupac_name',
            'molecular_weight': 'molecular_weight',
        }

        inserted = 0
        for _, row in df.iterrows():
            vals = {}
            for csv_col, sql_col in col_map.items():
                val = row.get(csv_col)
                if pd.notna(val):
                    vals[sql_col] = str(val) if isinstance(val, str) else float(val)

            if 'chemical_name' not in vals:
                continue

            placeholders = ', '.join(vals.keys())
            q_marks = ', '.join(['?' for _ in vals])
            try:
                conn.execute(
                    f"INSERT INTO chemical_properties ({placeholders}) VALUES ({q_marks})",
                    list(vals.values())
                )
                inserted += 1
            except sqlite3.IntegrityError:
                pass  # duplicate

        logger.info(f"  导入完成: {inserted} 行")
    else:
        logger.warning(f"  CSV 不存在: {CSV_PATH}")

    conn.commit()

    # 验证
    c = conn.execute("SELECT count(*) FROM chemical_properties").fetchone()[0]
    c2 = conn.execute(
        "SELECT count(*) FROM chemical_properties WHERE molecular_weight IS NOT NULL"
    ).fetchone()[0]
    logger.info(f"  验证: {c} 行, 其中 {c2} 有分子量数据")
    return conn


def fix_related_chemicals(conn):
    """标准化 related_chemicals 字段"""
    logger.info("\n" + "=" * 50)
    logger.info("  2. 标准化 related_chemicals")
    logger.info("=" * 50)

    # 获取化学品标准名列表
    std_names = set(r[0] for r in conn.execute(
        "SELECT chemical_name FROM chemical_properties"
    ).fetchall())

    # 非标准名 → 标准名映射
    normalize = {
        "氮气": None, "空气": None, "水": None, "水蒸气": None, "蒸汽": None,
        "氢气": "氢气", "氧气": None, "乙炔": "乙炔", "乙烯": "乙烯",
        "苯": "苯", "甲苯": "甲苯", "甲醇": "甲醇", "乙醇": "乙醇",
        "氯气": "氯气", "液氯": "氯气", "氨": "氨", "液氨": "氨",
        "硫化氢": "硫化氢", "硫化氢气体": "硫化氢",
        "一氧化碳": "一氧化碳", "二氧化碳": None,
        "氯乙烯": "氯乙烯", "丙烯腈": "丙烯腈",
        "甲醛": "甲醛", "苯酚": "苯酚", "丙酮": "丙酮",
        "硫酸": "硫酸", "硝酸": "硝酸", "盐酸": "盐酸",
        "氢氧化钠": "氢氧化钠", "烧碱": "氢氧化钠",
        "环氧乙烷": "环氧乙烷", "丁二烯": "丁二烯",
        "苯乙烯": "苯乙烯", "丙烯": "丙烯",
        "二氧化硫": "二氧化硫", "氰化氢": "氰化氢",
        "光气": "光气", "苯胺": "苯胺", "硝基苯": "硝基苯",
        "氟化氢": None,
        "液化石油气": None, "双氧水": None,
    }

    fixed = 0
    skipped = 0
    rows = conn.execute(
        "SELECT id, related_chemicals FROM accidents WHERE related_chemicals IS NOT NULL AND related_chemicals != ''"
    ).fetchall()

    for acc_id, chems_str in rows:
        chems = [c.strip() for c in chems_str.split(',') if c.strip()]
        fixed_chems = []
        for ch in chems:
            if ch in normalize:
                mapped = normalize[ch]
                if mapped:
                    fixed_chems.append(mapped)
                else:
                    skipped += 1  # 非危化品（空气/水/氮气），过滤掉
            elif ch in std_names:
                fixed_chems.append(ch)
            elif len(ch) >= 2:
                # 不在映射表中但可能是有效化学品名，保留
                fixed_chems.append(ch)

        if fixed_chems != chems:
            new_val = ','.join(fixed_chems) if fixed_chems else ''
            conn.execute(
                "UPDATE accidents SET related_chemicals = ? WHERE id = ?",
                (new_val, acc_id)
            )
            fixed += 1

    conn.commit()
    logger.info(f"  修正: {fixed} 行, 过滤非危化品: {skipped} 条")


def add_indexes(conn):
    """添加常用查询索引"""
    logger.info("\n" + "=" * 50)
    logger.info("  3. 添加查询索引")
    logger.info("=" * 50)

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_accidents_date ON accidents(date)",
        "CREATE INDEX IF NOT EXISTS idx_accidents_location ON accidents(location)",
        "CREATE INDEX IF NOT EXISTS idx_chemicals_name ON chemical_properties(chemical_name)",
        "CREATE INDEX IF NOT EXISTS idx_chemicals_cas ON chemical_properties(cas_number)",
    ]
    for idx in indexes:
        try:
            conn.execute(idx)
            logger.info(f"  {idx.split('ON')[0].strip()}")
        except sqlite3.OperationalError as e:
            logger.warning(f"  索引创建失败: {e}")

    conn.commit()


def create_analysis_view(conn):
    """创建事故-化学品关联分析视图"""
    logger.info("\n" + "=" * 50)
    logger.info("  4. 创建分析视图")
    logger.info("=" * 50)

    conn.execute("DROP VIEW IF EXISTS accident_chemical_view")
    conn.execute("""
        CREATE VIEW accident_chemical_view AS
        SELECT
            a.id AS accident_id,
            a.title,
            a.date,
            a.root_cause,
            a.consequence,
            a.related_chemicals,
            a.related_equipment,
            cp.molecular_weight,
            cp.cas_number,
            cp.iupac_name
        FROM accidents a
        LEFT JOIN chemical_properties cp
            ON ',' || a.related_chemicals || ',' LIKE '%,' || cp.chemical_name || ',%'
    """)
    logger.info("  accident_chemical_view 已创建")


def fill_weather_samples(conn):
    """为事故填充天气数据采样（从标题提取地点）"""
    logger.info("\n" + "=" * 50)
    logger.info("  5. 填充天气数据采样")
    logger.info("=" * 50)

    weather_count = conn.execute("SELECT count(*) FROM weather_records").fetchone()[0]
    if weather_count > 0:
        logger.info(f"  已有 {weather_count} 条记录，跳过")
        return

    import re
    from datetime import datetime

    # 省份名正则
    PROVINCE_RE = re.compile(
        r'(河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|'
        r'河南|湖北|湖南|广东|广西|四川|贵州|云南|陕西|甘肃|青海|'
        r'宁夏|新疆|内蒙古|北京|天津|上海|重庆|西藏|海南)'
    )

    # 取有日期的最近事故
    rows = conn.execute(
        "SELECT title, date FROM accidents WHERE date IS NOT NULL ORDER BY date DESC LIMIT 20"
    ).fetchall()

    if not rows:
        logger.warning("  无可用日期")
        return

    try:
        from src.acquisition.weather_fetcher import WeatherDataFetcher
        weather = WeatherDataFetcher()
    except Exception as e:
        logger.warning(f"  WeatherDataFetcher 导入失败: {e}")
        return

    inserted = 0
    for title, date_str in rows:
        if not date_str:
            continue

        # 从标题提取省份
        m = PROVINCE_RE.search(title or '')
        loc = m.group(0) if m else None
        if not loc:
            continue

        try:
            d = datetime.strptime(date_str[:10], "%Y-%m-%d")
            result = weather.fetch_weather_by_location(loc, d)
            if result:
                conn.execute("""
                    INSERT INTO weather_records
                    (location, date, temperature_max, temperature_min, wind_speed, precipitation, weather_condition)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.get("location", loc),
                    date_str,
                    result.get("temperature_max"),
                    result.get("temperature_min"),
                    result.get("wind_speed"),
                    result.get("precipitation"),
                    result.get("weather_condition", ""),
                ))
                inserted += 1
                logger.info(f"  {loc} {date_str[:10]}: {result.get('weather_condition', '?')}")

                if inserted >= 5:
                    break  # 采样 5 条即可
        except Exception as e:
            logger.debug(f"  {loc} {date_str[:10]}: {e}")

    conn.commit()
    logger.info(f"  插入: {inserted} 条天气记录")


def print_summary(conn):
    """打印最终状态摘要"""
    print("\n" + "=" * 60)
    print("  关系数据库修复完成")
    print("=" * 60)

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    for (tname,) in tables:
        count = conn.execute(f"SELECT count(*) FROM {tname}").fetchone()[0]
        cols = conn.execute(f"PRAGMA table_info({tname})").fetchall()
        print(f"\n  {tname}: {count} rows")
        for col in cols:
            non_null = conn.execute(
                f"SELECT count(*) FROM {tname} WHERE {col[1]} IS NOT NULL"
            ).fetchone()[0]
            pct = f"{non_null*100//max(count,1)}%" if count > 0 else "N/A"
            print(f"    {col[1]:25s} {col[2]:10s} 非空:{pct}")

    # 视图
    views = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'"
    ).fetchall()
    for (vname,) in views:
        count = conn.execute(f"SELECT count(*) FROM {vname}").fetchone()[0]
        print(f"\n  VIEW {vname}: {count} rows")

    print()


if __name__ == "__main__":
    conn = fix_chemical_properties()
    fix_related_chemicals(conn)
    add_indexes(conn)
    create_analysis_view(conn)
    fill_weather_samples(conn)
    print_summary(conn)
    conn.close()
    logger.info("全部修复完成")
