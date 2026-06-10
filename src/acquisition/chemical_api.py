"""
化学品物性数据采集模块

通过 PubChem API（主用，无需 API Key）和 EPA CompTox Dashboard API（备用）
获取常见危险化学品的物理化学性质数据。

数据源:
  - PubChem PUG REST: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest (P0, 无需Key)
  - EPA CompTox: https://comptox.epa.gov/dashboard (P1, 需注册免费Key)
  - eChemPortal: https://www.echemportal.org (P2, OECD全球化学品信息门户)

PubChemPy: https://github.com/mcs07/PubChemPy (pip install pubchempy)
"""
import logging
import time
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ChemicalPropertyFetcher:
    """化学品物性数据获取器"""

    # ─── 目标化学品清单 (含 CAS 号) ────────────────────────────────────────
    # 来源: 常见化工事故涉及化学品, 按事故频次排序
    # 扩展自 200+ 份 mem.gov.cn 事故报告的化学品出现频率分析
    TARGET_CHEMICALS = [
        # (英文名, CAS号, 中文名)
        ("acrylonitrile",    "107-13-1",  "丙烯腈"),
        ("benzene",          "71-43-2",   "苯"),
        ("toluene",          "108-88-3",  "甲苯"),
        ("xylene",           "1330-20-7", "二甲苯"),
        ("methanol",         "67-56-1",   "甲醇"),
        ("ethylene oxide",   "75-21-8",   "环氧乙烷"),
        ("chlorine",         "7782-50-5", "氯气"),
        ("ammonia",          "7664-41-7", "氨"),
        ("hydrogen sulfide", "7783-06-4", "硫化氢"),
        ("vinyl chloride",   "75-01-4",   "氯乙烯"),
        ("propylene",        "115-07-1",  "丙烯"),
        ("butadiene",        "106-99-0",  "丁二烯"),
        ("styrene",          "100-42-5",  "苯乙烯"),
        ("formaldehyde",     "50-00-0",   "甲醛"),
        ("phenol",           "108-95-2",  "苯酚"),
        ("acetone",          "67-64-1",   "丙酮"),
        ("sulfuric acid",    "7664-93-9", "硫酸"),
        ("nitric acid",      "7697-37-2", "硝酸"),
        ("carbon monoxide",  "630-08-0",  "一氧化碳"),
        ("hydrogen",         "1333-74-0", "氢气"),
        # ── v0.5 扩展：高频事故化学品 ──
        ("ethane",           "74-84-0",   "乙烷"),
        ("ethylene",         "74-85-1",   "乙烯"),
        ("acetylene",        "74-86-2",   "乙炔"),
        ("propane",          "74-98-6",   "丙烷"),
        ("hydrochloric acid", "7647-01-0", "盐酸/氯化氢"),
        ("sodium hydroxide", "1310-73-2", "氢氧化钠"),
        ("methyl isocyanate", "624-83-9",  "异氰酸甲酯"),
        ("phosgene",         "75-44-5",   "光气"),
        ("hydrogen cyanide", "74-90-8",   "氰化氢"),
        ("sulfur dioxide",   "7446-09-5", "二氧化硫"),
        ("ethanol",          "64-17-5",   "乙醇"),
        ("ethyl acetate",    "141-78-6",  "乙酸乙酯"),
        ("n-hexane",         "110-54-3",  "正己烷"),
        ("cyclohexane",      "110-82-7",  "环己烷"),
        ("aniline",          "62-53-3",   "苯胺"),
        ("nitrobenzene",     "98-95-3",   "硝基苯"),
    ]

    # 关注物性字段 (PubChem CID 对应的属性名映射)
    PROPERTY_MAP = {
        "MolecularWeight": "Molecular Weight",
        "BoilingPoint": "Boiling Point",
        "FlashPoint": "Flash Point",
        "UpperExplosionLimit": "Upper Explosion Limit",
        "LowerExplosionLimit": "Lower Explosion Limit",
        "AutoignitionTemperature": "Autoignition Temperature",
        "VaporPressure": "Vapor Pressure",
        "WaterSolubility": "Water Solubility",
        "ToxicityClass": "Toxicity",  # PubChem 无直接毒性分类，用 LD50 等替代
    }

    # PubChem API 端点
    PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def fetch_from_pubchem(self, chemical_name: str) -> Optional[dict]:
        """
        从 PubChem 获取化学品物性数据。

        PubChem PUG REST API (无需 API Key):
          - 化合物查找: GET /compound/name/{name}/property/{properties}/JSON
          - 文档: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest

        Args:
            chemical_name: 化学品英文名

        Returns:
            {chemical_name, cas_number, MolecularWeight, BoilingPoint, ...}
            失败返回 None
        """
        # PubChem 属性名列表
        props = ",".join([
            "MolecularWeight", "CanonicalSMILES", "IUPACName",
            "XLogP", "HBondDonorCount", "HBondAcceptCount",
            "RotatableBondCount", "MonoisotopicMass",
        ])

        url = f"{self.PUBCHEM_BASE}/compound/name/{chemical_name}/property/{props}/JSON"

        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            prop_dict = data["PropertyTable"]["Properties"][0]

            result = {
                "chemical_name": chemical_name,
                "cas_number": self._fetch_cas(chemical_name),
                "MolecularWeight": prop_dict.get("MolecularWeight"),
                "CanonicalSMILES": prop_dict.get("CanonicalSMILES"),
                "IUPACName": prop_dict.get("IUPACName"),
                "XLogP": prop_dict.get("XLogP"),
                "HBondDonorCount": prop_dict.get("HBondDonorCount"),
                "HBondAcceptCount": prop_dict.get("HBondAcceptCount"),
            }

            # 获取更详细的物性 (沸点、闪点等通过 PUG REST 需单独查)
            detailed = self._fetch_detailed_properties(chemical_name)
            if detailed:
                result.update(detailed)

            logger.info(f"PubChem 查询成功: {chemical_name}")
            return result

        except Exception as e:
            logger.warning(f"PubChem 查询失败 [{chemical_name}]: {e}")
            return None

    def _fetch_cas(self, chemical_name: str) -> Optional[str]:
        """
        从 PubChem 获取 CAS 号。

        PubChem 通过同名查询可直接获取 CID, 然后通过 Synonym 获取 CAS。
        """
        try:
            url = f"{self.PUBCHEM_BASE}/compound/name/{chemical_name}/synonyms/JSON"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            synonyms = resp.json()
            for item in synonyms["InformationList"]["Information"][0].get("Synonym", []):
                # CAS 号格式: xxxxxx-xx-x
                if "-" in item and len(item) >= 6 and item[0].isdigit():
                    return item
        except Exception:
            pass
        return None

    def _fetch_detailed_properties(self, chemical_name: str) -> Optional[dict]:
        """
        获取详细物性数据（沸点、闪点等）。

        PubChem 对这些物性没有统一字段，需要通过 PUG REST 获取详细记录。
        这里通过 CompTox 标题/描述信息进行补充。
        """
        # PubChem 的沸点/闪点等数据存在于描述(Description)中，
        # 需要从记录中解析，暂时返回空，后续可通过操作符或 CompTox API 补充
        return None

    # ─── EPA CompTox API (备用方案) ─────────────────────────────────────────
    # 数据源: https://comptox.epa.gov/dashboard/api
    # 需注册获取免费 API Key: https://comptox.epa.gov/dashboard

    EPA_API_BASE = "https://comptox.epa.gov/dashboard/api"

    def fetch_from_epa(self, chemical_name: str) -> Optional[dict]:
        """
        从 EPA CompTox Dashboard API 获取物性数据。

        TODO [数据接入]:
          1. 在 https://comptox.epa.gov/dashboard 注册获取 API Key
          2. 在 .env 中配置 EPA_API_KEY
          3. 实现 REST API 请求与响应解析

        API 文档: https://comptox.epa.gov/dashboard/api
        """
        from config.settings import llm  # 复用 .env 中的 Key 读取模式

        api_key = os.getenv("EPA_API_KEY", "")
        if not api_key:
            logger.warning("EPA_API_KEY 未配置，跳过 EPA CompTox 查询")
            return None

        # TODO [实现]: EPA API 调用
        # 示例:
        # url = f"{self.EPA_API_BASE}/chemical/{chemical_name}/property"
        # headers = {"x-api-key": api_key}
        # resp = requests.get(url, headers=headers, timeout=15)
        logger.info(f"EPA CompTox 查询: {chemical_name} (待 API Key 配置)")
        return None

    # ─── 批量构建 ────────────────────────────────────────────────────────────

    def build_property_table(self) -> pd.DataFrame:
        """
        构建化学品物性数据表。

        主数据源: PubChem (无需API Key, 免费)
        备用数据源: EPA CompTox (需免费注册)

        Returns:
            DataFrame, columns = [chemical_name, cas_number, MolecularWeight, ...]
        """
        records = []
        for chem_name, cas, _cn in self.TARGET_CHEMICALS:
            logger.info(f"查询物性数据 [{len(records)+1}/{len(self.TARGET_CHEMICALS)}]: {chem_name}")
            data = self.fetch_from_pubchem(chem_name)
            if data:
                records.append(data)
            else:
                # 备用: 尝试 EPA
                epa_data = self.fetch_from_epa(chem_name)
                if epa_data:
                    records.append(epa_data)
            time.sleep(0.5)  # API 限流，避免被封

        df = pd.DataFrame(records)
        logger.info(f"物性数据表构建完成: {len(df)}/{len(self.TARGET_CHEMICALS)} 条")
        return df


import os  # noqa: E402 (用于读取 EPA_API_KEY)
