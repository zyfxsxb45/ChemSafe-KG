"""
多源数据融合模块

将事故报告、化学品物性、气象数据等多源数据关联整合为统一分析视图。
支持 Pandas DataFrame 级别的关联操作和 Neo4j 图数据级别的融合。
"""
import logging
import re
from typing import Optional, Dict, List
from datetime import datetime, date
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# 化学品名标准化映射（常见别名 → 标准名）
CHEM_NAME_NORMALIZE = {
    "苯": "苯", "纯苯": "苯", "粗苯": "苯",
    "甲苯": "甲苯", "二甲苯": "二甲苯",
    "苯乙烯": "苯乙烯",
    "丙烯腈": "丙烯腈",
    "氯气": "氯气", "液氯": "氯气",
    "氨": "氨", "液氨": "氨", "氨气": "氨",
    "硫化氢": "硫化氢",
    "氯乙烯": "氯乙烯",
    "甲醇": "甲醇",
    "乙醇": "乙醇",
    "甲醛": "甲醛",
    "乙炔": "乙炔",
    "氢气": "氢气",
    "一氧化碳": "一氧化碳", "CO": "一氧化碳",
    "二氧化硫": "二氧化硫", "SO2": "二氧化硫",
    "氮氧化物": "氮氧化物", "NOx": "氮氧化物",
    "氰化氢": "氰化氢",
    "光气": "光气",
    "硫酸": "硫酸", "浓硫酸": "硫酸",
    "盐酸": "盐酸",
    "硝酸": "硝酸",
    "氢氧化钠": "氢氧化钠", "烧碱": "氢氧化钠",
    "环氧乙烷": "环氧乙烷",
    "丙烯": "丙烯",
    "丁二烯": "丁二烯",
    "异氰酸甲酯": "异氰酸甲酯", "MIC": "异氰酸甲酯",
}

# 从事故文本中提取化学品名称
_CHEM_PATTERN = re.compile(
    r'(?:液|气|纯|粗|浓|稀)?(?:'
    r'氯乙烯|氯气|液氯|液氨|氨气|硫化氢|丙烯腈|苯乙烯|苯酚'
    r'|甲醇|乙醇|甲醛|乙炔|氢气|一氧化碳|二氧化硫|氮氧化物|氰化氢|光气'
    r'|硫酸|盐酸|硝酸|氢氧化钠|烧碱|环氧乙烷|丙烯|丁二烯|异氰酸甲酯'
    r'|苯|甲苯|二甲苯|氨|甲烷|乙烷|丙烷|丁烷'
    r')'
)


class DataMerger:
    """多源数据融合器"""

    # ── 事故 ↔ 化学品关联 ─────────────────────────────────────────────────
    def merge_accident_with_chemicals(
        self,
        accidents: pd.DataFrame,
        chemicals: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        将事故记录与涉及的化学品物性数据关联。

        策略：从事故标题/描述/root_cause/consequence 中提取化学品名，
              与化学品物性表的标准名进行匹配。

        Args:
            accidents: 事故主表 DataFrame
            chemicals: 化学品物性表 DataFrame

        Returns:
            融合后的 DataFrame（添加化学品物性列）
        """
        if accidents.empty or chemicals.empty:
            logger.info("事故或化学品数据为空，跳过融合")
            return accidents

        df = accidents.copy()

        # 如果 already_related_chemicals 列存在，优先使用
        if "related_chemicals" in df.columns:
            # 展开多化学品（一对多）
            chem_records = []
            for _, acc in df.iterrows():
                chems_str = str(acc.get("related_chemicals", ""))
                if not chems_str or chems_str == "nan":
                    chem_records.append(acc.to_dict())
                    continue

                for chem_name in chems_str.split(","):
                    chem_name = chem_name.strip()
                    if not chem_name:
                        continue
                    norm_name = CHEM_NAME_NORMALIZE.get(chem_name, chem_name)
                    chem_row = chemicals[chemicals["chemical_name"] == norm_name]
                    record = acc.to_dict()
                    if not chem_row.empty:
                        cr = chem_row.iloc[0].to_dict()
                        for k, v in cr.items():
                            record[f"chem_{k}"] = v
                    record["_matched_chemical"] = norm_name
                    chem_records.append(record)

            if chem_records:
                result = pd.DataFrame(chem_records)
                logger.info(f"事故-化学品融合: {len(chem_records)} 条 (化学品列已展开)")
                return result

        # 降级：从文本中提取化学品名
        return self._extract_and_merge_chemicals(df, chemicals)

    def _extract_and_merge_chemicals(
        self, df: pd.DataFrame, chemicals: pd.DataFrame
    ) -> pd.DataFrame:
        """从事故文本中提取化学品名并与物性表匹配"""
        text_cols = ["title", "summary", "root_cause", "consequence"]
        available_cols = [c for c in text_cols if c in df.columns]

        if not available_cols:
            return df

        # 构建化学品物性索引
        chem_index = {}
        for _, row in chemicals.iterrows():
            name = str(row.get("chemical_name", ""))
            if name:
                chem_index[name] = row.to_dict()

        matched_chems = []
        for _, acc in df.iterrows():
            combined = " ".join(str(acc.get(c, "")) for c in available_cols)
            found = set()
            for m in _CHEM_PATTERN.finditer(combined):
                raw = m.group(0)
                norm = CHEM_NAME_NORMALIZE.get(raw, raw)
                found.add(norm)

            matched_chems.append(",".join(found) if found else "")

        df["_extracted_chemicals"] = matched_chems
        logger.info(f"从文本中提取化学品: {sum(1 for m in matched_chems if m)} 起事故有关联")
        return df

    # ── 事故 ↔ 气象关联 ────────────────────────────────────────────────────
    def merge_accident_with_weather(
        self,
        accidents: pd.DataFrame,
        weather: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        将事故记录与对应时间地点的气象数据关联。

        关联键: 日期（最近匹配）+ 地点

        Args:
            accidents: 事故主表
            weather: 气象数据表 (location, date, temperature_max, ...)

        Returns:
            融合后的 DataFrame
        """
        if accidents.empty or weather.empty:
            return accidents

        df = accidents.copy()

        if "date" not in df.columns:
            logger.warning("事故表缺少 date 列，无法关联气象数据")
            return df

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        weather["date"] = pd.to_datetime(weather["date"], errors="coerce")

        weather_cols = [c for c in weather.columns
                       if c not in ("id", "location", "date")]

        # 对于每起事故，找时空最近的气象记录
        weather_records = []
        for _, acc in df.iterrows():
            acc_date = acc["date"]
            acc_loc = str(acc.get("location", ""))

            if pd.isna(acc_date):
                weather_records.append({})
                continue

            # 匹配地点 + 日期最近
            candidates = weather.copy()
            if "location" in weather.columns:
                # 模糊地点匹配
                candidates = candidates[
                    candidates["location"].apply(
                        lambda x: any(p in str(acc_loc) for p in [str(x), str(x)[:2]])
                    )
                ]

            if candidates.empty:
                # 降级：只用日期匹配
                candidates = weather.copy()

            candidates["date_diff"] = (candidates["date"] - acc_date).abs()
            best = candidates.nsmallest(1, "date_diff")

            if not best.empty:
                record = {}
                for c in weather_cols:
                    record[f"weather_{c}"] = best.iloc[0][c]
                weather_records.append(record)
            else:
                weather_records.append({})

        # 合并气象列
        weather_df = pd.DataFrame(weather_records)
        for c in weather_df.columns:
            df[c] = weather_df[c].values

        matched = sum(1 for r in weather_records if r)
        logger.info(f"事故-气象融合: {matched}/{len(df)} 起事故匹配到气象数据")
        return df

    # ── 统一视图 ────────────────────────────────────────────────────────────
    def build_unified_view(
        self,
        accidents: pd.DataFrame,
        chemicals: Optional[pd.DataFrame] = None,
        weather: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        构建统一的多维事故分析视图。

        集成事故基础信息、化学品物性和天气数据。
        """
        df = accidents.copy()
        logger.info(f"构建统一视图: 基础 {len(df)} 条事故")

        if chemicals is not None and not chemicals.empty:
            df = self.merge_accident_with_chemicals(df, chemicals)

        if weather is not None and not weather.empty:
            df = self.merge_accident_with_weather(df, weather)

        logger.info(f"统一视图构建完成: {len(df)} 条记录, {len(df.columns)} 列")
        return df

    # ── Neo4j 图级别融合 ───────────────────────────────────────────────────
    def link_accident_nodes_to_chemicals(
        self,
        neo4j_client,
        chemicals: pd.DataFrame,
    ) -> int:
        """
        在 Neo4j 图数据库中将事故节点与化学品节点关联。

        为 Material 类型的节点添加来自 PubChem 的物化性质。

        Returns:
            成功关联的数量
        """
        if chemicals.empty or neo4j_client.graph is None:
            return 0

        props_to_add = [
            "cas_number", "boiling_point", "flash_point",
            "upper_explosion_limit", "lower_explosion_limit",
            "vapor_pressure", "toxicity_class",
        ]

        count = 0
        for _, row in chemicals.iterrows():
            chem_name = str(row.get("chemical_name", ""))
            if not chem_name:
                continue

            props = {}
            for p in props_to_add:
                val = row.get(p)
                if val is not None and not (isinstance(val, float) and np.isnan(val)):
                    props[p] = val

            if not props:
                continue

            try:
                set_clause = ", ".join(f"n.{k} = ${k}" for k in props)
                neo4j_client.graph.run(
                    f"MATCH (n:Material {{name: $name}}) SET {set_clause}",
                    name=chem_name, **props,
                )
                count += 1
            except Exception as e:
                logger.debug(f"Neo4j 化学品属性写入失败 [{chem_name}]: {e}")

        logger.info(f"Neo4j 化学品属性融合: {count} 个 Material 节点")
        return count

    # ── 统计摘要 ───────────────────────────────────────────────────────────
    def get_fusion_summary(self, df: pd.DataFrame) -> Dict:
        """生成融合统计摘要"""
        summary = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
        }

        # 化学品覆盖率
        chem_cols = [c for c in df.columns if c.startswith("chem_")]
        if chem_cols:
            summary["chemical_coverage"] = df[chem_cols[0]].notna().sum()
            summary["chemical_coverage_pct"] = round(
                summary["chemical_coverage"] / max(len(df), 1) * 100, 1
            )
        else:
            summary["chemical_coverage"] = 0
            summary["chemical_coverage_pct"] = 0

        # 气象覆盖率
        weather_cols = [c for c in df.columns if c.startswith("weather_")]
        if weather_cols:
            summary["weather_coverage"] = df[weather_cols[0]].notna().sum()
            summary["weather_coverage_pct"] = round(
                summary["weather_coverage"] / max(len(df), 1) * 100, 1
            )
        else:
            summary["weather_coverage"] = 0
            summary["weather_coverage_pct"] = 0

        return summary
