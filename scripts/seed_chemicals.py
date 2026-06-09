"""手动化学品物性表填充 — 直接插入50+种高频化学品"""
import os, sys, sqlite3
from pathlib import Path
os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

DB = "data/processed/chemsafe.db"

# (chemical_name, english_name, cas_number, iupac_name, molecular_weight)
DATA = [
    # 高频化学品
    ("氮气", "Nitrogen", "7727-37-9", "dinitrogen", 28.01),
    ("煤气", "Coal gas", "", "", None),
    ("油气", "Petroleum gas", "", "", None),
    ("导热油", "Heat transfer oil", "", "", None),
    ("硝酸铵", "Ammonium nitrate", "6484-52-2", "ammonium nitrate", 80.04),
    ("汽油", "Gasoline", "8006-61-9", "gasoline", None),
    ("液化石油气", "Liquefied petroleum gas", "68476-85-7", "liquefied petroleum gas", None),
    ("双氧水", "Hydrogen peroxide", "7722-84-1", "hydrogen peroxide", 34.01),
    ("原油", "Crude oil", "8002-05-9", "petroleum", None),
    ("丙烷", "Propane", "74-98-6", "propane", 44.10),
    ("液氨", "Ammonia (liquid)", "7664-41-7", "ammonia", 17.03),
    ("二硫化碳", "Carbon disulfide", "75-15-0", "methanedithione", 76.14),
    ("液氯", "Chlorine (liquid)", "7782-50-5", "dichlorine", 70.91),
    ("甲硫醇", "Methanethiol", "74-93-1", "methanethiol", 48.11),
    ("石脑油", "Naphtha", "8030-30-6", "naphtha", None),
    ("硫磺", "Sulfur", "7704-34-9", "sulfur", 32.07),
    ("甲烷", "Methane", "74-82-8", "methane", 16.04),
    ("乙炔", "Acetylene", "74-86-2", "acetylene", 26.04),
    ("乙醇", "Ethanol", "64-17-5", "ethanol", 46.07),
    ("苯酚", "Phenol", "108-95-2", "phenol", 94.11),
    ("丙酮", "Acetone", "67-64-1", "acetone", 58.08),
    ("氢氧化钠", "Sodium hydroxide", "1310-73-2", "sodium hydroxide", 40.00),
    ("盐酸", "Hydrochloric acid", "7647-01-0", "hydrogen chloride", 36.46),
    ("光气", "Phosgene", "75-44-5", "carbonyl dichloride", 98.92),
    ("氰化氢", "Hydrogen cyanide", "74-90-8", "formonitrile", 27.03),
    ("丙烯", "Propylene", "115-07-1", "propene", 42.08),
    ("丁二烯", "1,3-Butadiene", "106-99-0", "buta-1,3-diene", 54.09),
    ("硫酸", "Sulfuric acid", "7664-93-9", "sulfuric acid", 98.08),
    ("硝酸", "Nitric acid", "7697-37-2", "nitric acid", 63.01),
    ("一氧化碳", "Carbon monoxide", "630-08-0", "carbon monoxide", 28.01),
    ("氢气", "Hydrogen", "1333-74-0", "dihydrogen", 2.02),
    ("乙烷", "Ethane", "74-84-0", "ethane", 30.07),
    ("乙烯", "Ethylene", "74-85-1", "ethene", 28.05),
    ("二甲苯", "Xylene", "1330-20-7", "xylene", 106.17),
    ("二氧化硫", "Sulfur dioxide", "7446-09-5", "sulfur dioxide", 64.07),
    ("氨水", "Ammonium hydroxide", "1336-21-6", "ammonium hydroxide", 35.05),
    ("醋酸", "Acetic acid", "64-19-7", "acetic acid", 60.05),
    ("氢氟酸", "Hydrofluoric acid", "7664-39-3", "hydrogen fluoride", 20.01),
    ("次氯酸钠", "Sodium hypochlorite", "7681-52-9", "sodium hypochlorite", 74.44),
    ("硝基苯", "Nitrobenzene", "98-95-3", "nitrobenzene", 123.11),
    ("苯胺", "Aniline", "62-53-3", "aniline", 93.13),
    ("TDI", "Toluene diisocyanate", "584-84-9", "2,4-diisocyanato-1-methylbenzene", 174.16),
    ("TNT", "Trinitrotoluene", "118-96-7", "2-methyl-1,3,5-trinitrobenzene", 227.13),
    ("硫化钠", "Sodium sulfide", "1313-82-2", "sodium sulfide", 78.05),
    ("环氧乙烷", "Ethylene oxide", "75-21-8", "oxirane", 44.05),
    ("氯酸钾", "Potassium chlorate", "3811-04-9", "potassium chlorate", 122.55),
    ("氢氟酸", "Hydrofluoric acid", "7664-39-3", "hydrogen fluoride", 20.01),
    ("高锰酸钾", "Potassium permanganate", "7722-64-7", "potassium permanganate", 158.03),
    ("过氧化苯甲酰", "Benzoyl peroxide", "94-36-0", "dibenzoyl peroxide", 242.23),
    ("磷酸", "Phosphoric acid", "7664-38-2", "phosphoric acid", 98.00),
    ("氰化钠", "Sodium cyanide", "143-33-9", "sodium cyanide", 49.01),
    ("三氯化磷", "Phosphorus trichloride", "7719-12-2", "phosphorus trichloride", 137.33),
    ("二氧化氯", "Chlorine dioxide", "10049-04-4", "chlorine dioxide", 67.45),
    ("重铬酸钠", "Sodium dichromate", "10588-01-9", "sodium dichromate", 261.97),
    ("四氯化碳", "Carbon tetrachloride", "56-23-5", "tetrachloromethane", 153.82),
    ("三氯甲烷", "Chloroform", "67-66-3", "chloroform", 119.38),
    ("硝酸钾", "Potassium nitrate", "7757-79-1", "potassium nitrate", 101.10),
    ("硫酸二甲酯", "Dimethyl sulfate", "77-78-1", "dimethyl sulfate", 126.13),
]

def main():
    conn = sqlite3.connect(DB)
    existing = set(r[0] for r in conn.execute("SELECT chemical_name FROM chemical_properties").fetchall())
    new = 0
    for name, en, cas, iupac, mw in DATA:
        if name in existing:
            continue
        conn.execute("""
            INSERT OR IGNORE INTO chemical_properties
            (chemical_name, english_name, cas_number, iupac_name, molecular_weight)
            VALUES (?, ?, ?, ?, ?)
        """, (name, en, cas, iupac, mw))
        new += 1
    conn.commit()
    total = conn.execute("SELECT count(*) FROM chemical_properties").fetchone()[0]
    conn.close()
    print(f"新增: {new}, 总计: {total}")

if __name__ == "__main__":
    main()
