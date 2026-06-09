"""
化学品物性全量拓充脚本

从 accidents 表的 related_chemicals 字段提取全部化学品名，
通过 PubChem API 获取物性数据，写入 chemical_properties 表。

运行: python scripts/enrich_chemicals.py
预计耗时: ~10分钟 (400种化学品 × ~1.5秒/种)
"""
import os, sys, re, time, logging
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("enrich_chem")

import sqlite3
import requests

DB = "data/processed/chemsafe.db"

# 化学品名标准化：中文俗名 → PubChem可查询的英文名
NAME_MAP = {
    "氮气": "nitrogen", "煤气": "coal gas", "油气": "petroleum", "导热油": "heat transfer oil",
    "汽油": "gasoline", "液化石油气": "liquefied petroleum gas", "双氧水": "hydrogen peroxide",
    "物料": None, "原油": "crude oil", "丙烷": "propane", "液氨": "ammonia",
    "二硫化碳": "carbon disulfide", "可燃气体": None, "液氯": "chlorine",
    "硫化钠": "sodium sulfide", "蒸汽": None, "甲硫醇": "methanethiol",
    "石脑油": "naphtha", "烃类": None, "乙炔": "acetylene", "环氧乙烷": "ethylene oxide",
    "乙醇": "ethanol", "苯酚": "phenol", "丙酮": "acetone", "甲醛": "formaldehyde",
    "氢氧化钠": "sodium hydroxide", "盐酸": "hydrochloric acid", "光气": "phosgene",
    "氰化氢": "hydrogen cyanide", "丙烯": "propylene", "丁二烯": "butadiene",
    "苯乙烯": "styrene", "硫酸": "sulfuric acid", "硝酸": "nitric acid",
    "一氧化碳": "carbon monoxide", "氢气": "hydrogen", "乙烷": "ethane",
    "乙烯": "ethylene", "二甲苯": "xylene", "甲苯": "toluene",
    "苯": "benzene", "甲醇": "methanol", "硫化氢": "hydrogen sulfide",
    "氯乙烯": "vinyl chloride", "氯气": "chlorine", "氨": "ammonia",
    "丙烯腈": "acrylonitrile", "异氰酸甲酯": "methyl isocyanate",
    "硫磺": "sulfur", "甲烷": "methane", "二氧化碳": "carbon dioxide",
    "二氧化硫": "sulfur dioxide", "氮氧化物": "nitrogen oxides",
    "氨水": "ammonium hydroxide", "醋酸": "acetic acid", "磷酸": "phosphoric acid",
    "氢氟酸": "hydrofluoric acid", "次氯酸钠": "sodium hypochlorite",
    "高锰酸钾": "potassium permanganate", "过氧化氢": "hydrogen peroxide",
    "重铬酸钠": "sodium dichromate", "氰化钠": "sodium cyanide",
    "三氯化磷": "phosphorus trichloride", "三氯氧磷": "phosphorus oxychloride",
    "硝基苯": "nitrobenzene", "苯胺": "aniline", "对硝基甲苯": "p-nitrotoluene",
    "TDI": "toluene diisocyanate", "MDI": "methylene diphenyl diisocyanate",
    "DNT": "dinitrotoluene", "TNT": "trinitrotoluene",
    "硝酸铵": "ammonium nitrate", "硝酸钾": "potassium nitrate",
    "氯酸钾": "potassium chlorate", "过氧化苯甲酰": "benzoyl peroxide",
}


def pubchem_lookup(name: str) -> dict | None:
    """通过 PubChem REST API 按名称查询化合物物性"""
    en_name = NAME_MAP.get(name)
    if en_name is None and name in NAME_MAP:
        return None  # explicitly mapped to skip

    query = en_name or name
    try:
        # Step 1: search by name → get CID
        resp = requests.get(
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{query}/cids/JSON",
            timeout=10
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        cids = data.get("IdentifierList", {}).get("CID", [])
        if not cids:
            return None
        cid = cids[0]

        # Step 2: get properties
        props_url = (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/"
            f"MolecularWeight,IUPACName,MolecularFormula,CanonicalSMILES/JSON"
        )
        resp2 = requests.get(props_url, timeout=10)
        if resp2.status_code != 200:
            return None
        props = resp2.json().get("PropertyTable", {}).get("Properties", [{}])[0]

        return {
            "chemical_name": name,
            "english_name": en_name or name,
            "cas_number": "",
            "iupac_name": props.get("IUPACName", ""),
            "molecular_weight": props.get("MolecularWeight"),
            "molecular_formula": props.get("MolecularFormula", ""),
        }
    except Exception:
        return None


def main():
    conn = sqlite3.connect(DB)

    # Collect all chemicals from accidents
    all_chems = set()
    for (val,) in conn.execute(
        "SELECT related_chemicals FROM accidents WHERE related_chemicals != ''"
    ).fetchall():
        for chem in val.split(","):
            chem = chem.strip()
            if len(chem) >= 2:
                all_chems.add(chem)

    # Already existing
    existing = set(
        r[0] for r in conn.execute("SELECT chemical_name FROM chemical_properties").fetchall()
    )
    to_fetch = sorted(all_chems - existing)

    logger.info(f"化学品总数: {len(all_chems)}, 已有: {len(existing)}, 待获取: {len(to_fetch)}")

    new_count = 0
    skip_count = 0
    fail_count = 0

    for i, chem in enumerate(to_fetch):
        # Check if explicitly unmappable
        if chem in NAME_MAP and NAME_MAP[chem] is None:
            skip_count += 1
            continue

        props = pubchem_lookup(chem)
        if props:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO chemical_properties
                    (chemical_name, english_name, cas_number, iupac_name, molecular_weight)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    props["chemical_name"], props["english_name"],
                    props["cas_number"], props["iupac_name"],
                    props["molecular_weight"],
                ))
                conn.commit()
                new_count += 1
            except Exception:
                fail_count += 1
        else:
            fail_count += 1

        if (i + 1) % 20 == 0:
            logger.info(f"  进度 {i+1}/{len(to_fetch)}: +{new_count}新, {fail_count}失败, {skip_count}跳过")

        if (i + 1) % 10 == 0:
            time.sleep(0.3)  # rate limit

    total = conn.execute("SELECT count(*) FROM chemical_properties").fetchone()[0]
    conn.close()

    logger.info(f"完成! chemical_properties: {total} 种")
    logger.info(f"  新增: {new_count}, 失败: {fail_count}, 跳过: {skip_count}")


if __name__ == "__main__":
    main()
