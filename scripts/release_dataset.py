"""把 SQLite 最新数据导出到 data/release/"""
import csv, sqlite3, os

DB = "data/processed/chemsafe.db"
RELEASE = "data/release"
os.makedirs(RELEASE, exist_ok=True)

conn = sqlite3.connect(DB)

# accidents
with open(os.path.join(RELEASE, "accidents.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    cols = ["title","date","summary","root_cause","consequence","accident_type",
            "related_chemicals","related_equipment","source_url","location"]
    w.writerow(cols)
    for row in conn.execute(f"SELECT {','.join(cols)} FROM accidents"):
        w.writerow(row)
n = conn.execute("SELECT count(*) FROM accidents").fetchone()[0]
print(f"accidents.csv: {n} + header")

# chemical_properties
with open(os.path.join(RELEASE, "chemical_properties.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    header = ["chemical_name","cas_number","iupac_name","molecular_weight",
              "flash_point","lower_explosion_limit","toxicity_class"]
    w.writerow(header)
    for row in conn.execute(f"SELECT {','.join(header)} FROM chemical_properties"):
        w.writerow(row)
n = conn.execute("SELECT count(*) FROM chemical_properties").fetchone()[0]
print(f"chemical_properties.csv: {n} + header")

# weather_records
with open(os.path.join(RELEASE, "weather_records.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    cols = ["location","date","temperature_max","temperature_min",
            "humidity","wind_speed","precipitation","weather_condition"]
    w.writerow(cols)
    for row in conn.execute(f"SELECT {','.join(cols)} FROM weather_records"):
        w.writerow(row)
n = conn.execute("SELECT count(*) FROM weather_records").fetchone()[0]
print(f"weather_records.csv: {n} + header")

conn.close()
print("Done — all release CSVs exported.")
