"""
天气与地点数据填充脚本

1. 从 accidents 标题中提取省份/城市名，填充 location 字段
2. 对有日期+地点的记录，调用 Open-Meteo 获取历史天气

运行: python scripts/enrich_weather.py
预计耗时: ~2分钟 (提取地点) + ~5分钟/100条天气查询
"""
import os, sys, re, time, logging
from pathlib import Path
from datetime import datetime

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("enrich_weather")

import sqlite3
import requests

DB = "data/processed/chemsafe.db"

# 中国省份/直辖市列表
PROVINCES = [
    "北京", "天津", "上海", "重庆",
    "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "广西", "海南",
    "四川", "贵州", "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆",
    "内蒙古",
]

# 省份→坐标（经纬度，用于 Open-Meteo 查询）
PROVINCE_COORDS = {
    "北京": (39.90, 116.40), "天津": (39.13, 117.20), "上海": (31.23, 121.47),
    "重庆": (29.43, 106.91), "河北": (38.04, 114.50), "山西": (37.87, 112.55),
    "辽宁": (41.80, 123.43), "吉林": (43.88, 125.32), "黑龙江": (45.75, 126.63),
    "江苏": (32.06, 118.80), "浙江": (30.27, 120.15), "安徽": (31.86, 117.28),
    "福建": (26.07, 119.30), "江西": (28.68, 115.90), "山东": (36.67, 117.00),
    "河南": (34.76, 113.65), "湖北": (30.58, 114.30), "湖南": (28.19, 112.98),
    "广东": (23.13, 113.26), "广西": (22.82, 108.33), "海南": (20.02, 110.35),
    "四川": (30.57, 104.07), "贵州": (26.60, 106.72), "云南": (25.04, 102.71),
    "西藏": (29.65, 91.13), "陕西": (34.26, 108.94), "甘肃": (36.06, 103.83),
    "青海": (36.62, 101.78), "宁夏": (38.47, 106.27), "新疆": (43.79, 87.62),
    "内蒙古": (40.82, 111.75),
}


def extract_location(title: str) -> str:
    """从事故标题中提取省份名"""
    for p in PROVINCES:
        if p in title:
            return p
    return ""


def fetch_weather(lat: float, lon: float, date_str: str) -> dict | None:
    """从 Open-Meteo 获取指定日期和地点的历史天气"""
    try:
        url = (
            f"https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lat}&longitude={lon}"
            f"&start_date={date_str}&end_date={date_str}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
            f"&timezone=Asia/Shanghai"
        )
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        daily = data.get("daily", {})
        if not daily:
            return None
        return {
            "temperature_max": daily["temperature_2m_max"][0] if daily.get("temperature_2m_max") else None,
            "temperature_min": daily["temperature_2m_min"][0] if daily.get("temperature_2m_min") else None,
            "precipitation": daily["precipitation_sum"][0] if daily.get("precipitation_sum") else None,
            "wind_speed": daily["wind_speed_10m_max"][0] if daily.get("wind_speed_10m_max") else None,
        }
    except Exception:
        return None


def main():
    conn = sqlite3.connect(DB)

    # Step 1: 填充 location
    rows = conn.execute(
        "SELECT id, title FROM accidents WHERE location IS NULL OR location = ''"
    ).fetchall()

    location_updates = 0
    for rid, title in rows:
        loc = extract_location(title or "")
        if loc:
            conn.execute("UPDATE accidents SET location = ? WHERE id = ?", (loc, rid))
            location_updates += 1

    conn.commit()
    logger.info(f"地点填充: {location_updates}/{len(rows)} 条")

    # Step 2: 采样天气数据
    weather_rows = conn.execute("""
        SELECT id, location, date FROM accidents
        WHERE date IS NOT NULL AND location IS NOT NULL AND location != ''
        ORDER BY RANDOM() LIMIT 100
    """).fetchall()

    logger.info(f"天气采样: {len(weather_rows)} 条候选")
    weather_count = 0
    skip_count = 0

    for rid, loc, date_str in weather_rows:
        if loc not in PROVINCE_COORDS:
            skip_count += 1
            continue
        lat, lon = PROVINCE_COORDS[loc]
        weather = fetch_weather(lat, lon, date_str)
        if weather:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO weather_records
                    (location, date, temperature_max, temperature_min, wind_speed, precipitation)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (loc, date_str, weather["temperature_max"], weather["temperature_min"],
                      weather["wind_speed"], weather["precipitation"]))
                weather_count += 1
            except Exception:
                pass

        if (weather_count + skip_count) % 20 == 0:
            logger.info(f"  天气进度: {weather_count + skip_count}/{len(weather_rows)} (+{weather_count})")
        time.sleep(0.15)

    conn.commit()
    weather_total = conn.execute("SELECT count(*) FROM weather_records").fetchone()[0]
    conn.close()

    logger.info(f"天气填充: {weather_count} 条新增, 总计 {weather_total} 条")
    logger.info(f"地点覆盖率: {location_updates} 条有省份信息")


if __name__ == "__main__":
    main()
