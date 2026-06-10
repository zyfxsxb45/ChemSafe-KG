"""
气象/环境数据采集模块

获取事故发生时对应地点和时间的天气数据。

数据源（按优先级排序）:
  P0 - Open-Meteo: https://open-meteo.com (免费, 无需API Key, 历史数据自1940年)
  P1 - NOAA NCEI: https://www.ncei.noaa.gov/access (免费公开)
  P2 - 中国气象数据网: http://data.cma.cn (免费注册使用)
  P2 - APiHZ历史天气: https://cn.apihz.cn (国内站点补充)

Open-Meteo 优势:
  - 完全免费，无需注册，无需 API Key
  - 全球覆盖，历史天气自1940年起
  - 支持逐小时/逐日粒度
  - Python 请求即可调用，响应为 JSON
"""
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple

import pandas as pd
import requests
import concurrent.futures

logger = logging.getLogger(__name__)


class WeatherDataFetcher:
    """气象数据获取器"""

    # ─── Open-Meteo API (P0, 免费, 无需 Key) ──────────────────────────────
    # 文档: https://open-meteo.com/en/docs/historical-weather-api
    OPEN_METEO_BASE = "https://archive-api.open-meteo.com/v1/archive"

    # 天气编码 → 中文描述
    WEATHER_CODES = {
        0: "晴天", 1: "大部晴朗", 2: "局部多云", 3: "多云",
        45: "雾", 48: "雾凇",
        51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
        56: "冻毛毛雨(小)", 57: "冻毛毛雨(大)",
        61: "小雨", 63: "中雨", 65: "大雨",
        66: "冻雨(小)", 67: "冻雨(大)",
        71: "小雪", 73: "中雪", 75: "大雪",
        77: "雪粒",
        80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
        85: "小阵雪", 86: "大阵雪",
        95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
    }

    # ─── 中文地名 → (纬度, 经度) 映射 ─────────────────────────────────
    # 已覆盖 34 个省级行政区
    LOCATION_COORDS = {
        # 中国各省份（省/市/自治区）
        "江苏省": (33.0, 120.0), "江苏省南京市": (32.06, 118.80), "江苏省盐城市": (33.35, 120.16),
        "山东省": (36.0, 118.0), "山东省济南市": (36.65, 116.99),
        "浙江省": (29.0, 120.0), "广东省": (23.0, 114.0),
        "河北省": (38.0, 115.0), "河南省": (34.0, 113.0),
        "四川省": (30.0, 104.0), "湖北省": (30.5, 114.3),
        "湖南省": (28.0, 113.0), "安徽省": (31.8, 117.3),
        "江西省": (28.7, 115.9), "福建省": (26.0, 118.0),
        "山西省": (37.8, 112.5), "陕西省": (34.3, 108.9),
        "甘肃省": (36.0, 103.8), "辽宁省": (41.8, 123.4),
        "吉林省": (43.9, 125.3), "黑龙江省": (45.8, 126.5),
        "云南省": (25.0, 102.7), "贵州省": (26.6, 106.7),
        "广西": (22.8, 108.4), "内蒙古": (40.8, 111.8),
        "宁夏": (38.5, 106.3), "新疆": (43.8, 87.6),
        "西藏": (30.7, 91.1), "青海": (36.6, 101.8), "海南": (20.0, 110.4),
        "上海市": (31.23, 121.47),
        "北京市": (39.90, 116.41),
        "天津市": (39.13, 117.19), "天津": (39.13, 117.19),
        "重庆市": (29.53, 106.50), "重庆": (29.53, 106.50),
        # 美国主要化工区域 (为CSB事故数据准备)
        "Texas": (31.0, -100.0),
        "Louisiana": (31.0, -92.0),
        "California": (36.0, -119.0),
        "Ohio": (40.0, -83.0),
    }

    def _geocode(self, location: str) -> Optional[Tuple[float, float]]:
        """
        地点名 → (纬度, 经度) 转换。

        优先使用内置映射，后续可接入免费地理编码 API。

        TODO [完善]:
          - 使用 Nominatim (OpenStreetMap) 免费地理编码
          - 使用 Open-Meteo 自带的 geocoding API:
            https://geocoding-api.open-meteo.com/v1/search?name={city}
        """
        # 1. 精确匹配
        if location in self.LOCATION_COORDS:
            return self.LOCATION_COORDS[location]

        # 2. 模糊匹配 (包含关系)
        for name, coords in self.LOCATION_COORDS.items():
            if location.startswith(name) or name.startswith(location):
                return coords

        # 3. 调用免费地理编码 API (备用)
        # TODO [完善]: 接入 Open-Meteo Geocoding API
        # url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
        logger.warning(f"未找到地点 '{location}' 的坐标，请添加到 LOCATION_COORDS")
        return None

    def fetch_weather_by_location(
        self,
        location: str,
        date: datetime,
    ) -> Optional[Dict]:
        """
        获取指定地点在指定日期的天气数据。

        使用 Open-Meteo Archive API (免费, 无需 API Key, 数据自1940年)。

        Args:
            location: 事故地点 (如 "江苏省盐城市")
            date: 事故日期

        Returns:
            {
                "temperature_max": 35.0,    # 最高气温(℃)
                "temperature_min": 22.0,    # 最低气温(℃)
                "humidity": 65,             # 平均相对湿度(%)
                "wind_speed": 3.5,          # 最大风速(m/s)
                "precipitation": 0.0,       # 总降水量(mm)
                "weather_code": 0,          # WMO天气编码
                "weather_condition": "晴天", # 天气状况中文描述
            }
            失败返回 None
        """
        coords = self._geocode(location)
        if not coords:
            return None

        lat, lon = coords
        date_str = date.strftime("%Y-%m-%d")

        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": date_str,
            "end_date": date_str,
            "daily": "temperature_2m_max,temperature_2m_min,"
                     "precipitation_sum,windspeed_10m_max,"
                     "weathercode",
            "timezone": "auto",
        }

        try:
            resp = requests.get(
                self.OPEN_METEO_BASE,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            daily = data.get("daily", {})
            if not daily or not daily.get("time"):
                logger.warning(f"Open-Meteo 无数据: {location} {date_str}")
                return None

            # 提取每日数据 (取第一条)
            wmo_code = daily["weathercode"][0]
            weather_condition = self.WEATHER_CODES.get(wmo_code, f"未知({wmo_code})")

            result = {
                "location": location,
                "date": date_str,
                "temperature_max": daily.get("temperature_2m_max", [None])[0],
                "temperature_min": daily.get("temperature_2m_min", [None])[0],
                "precipitation": daily.get("precipitation_sum", [None])[0],
                "wind_speed": daily.get("windspeed_10m_max", [None])[0],
                "weather_code": wmo_code,
                "weather_condition": weather_condition,
                "latitude": lat,
                "longitude": lon,
            }
            logger.info(f"天气查询成功: {location} {date_str} -> {weather_condition}")
            return result

        except requests.exceptions.RequestException as e:
            logger.warning(f"Open-Meteo 请求失败 [{location} {date_str}]: {e}")
            return None

    def batch_fetch(
        self,
        accident_records: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        批量查询事故对应的天气数据。

        Args:
            accident_records: DataFrame 需包含 location, date 列

        Returns:
            DataFrame: 原始事故记录 + 天气字段

        TODO [完善]:
          1. 并发请求加速 (asyncio / ThreadPool)
          2. 请求失败重试
          3. 缓存已查询结果 (避免重复请求)
        """
        def fetch_single(row):
            loc = row.get("location", "")
            dt = row.get("date")
            if not loc or not dt:
                return None
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt)
            return self.fetch_weather_by_location(loc, dt)

        weather_rows = []
        # 使用线程池并发请求 API，大幅减少网络 I/O 等待时间
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_single, row) for _, row in accident_records.iterrows()]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    weather_rows.append(res)

        if weather_rows:
            weather_df = pd.DataFrame(weather_rows)
            # 合并到原数据
            result = accident_records.merge(
                weather_df,
                on=["location", "date"],
                how="left",
            )
            return result

        return accident_records
