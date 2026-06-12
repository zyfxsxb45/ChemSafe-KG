"""用去重后数据重新导出 release CSV"""
import csv, json, sqlite3
import pandas as pd

DB = "data/processed/chemsafe.db"
conn = sqlite3.connect(DB)

# Load and dedup
df = pd.read_sql("SELECT * FROM accidents", conn)
with open("data/processed/dedup_mapping.json") as f:
    dup_ids = set(int(k) for k in json.load(f).keys())

# Check overlap
before = len(df)
dup_in_df = sum(1 for i in df["id"] if i in dup_ids)
print(f"Before: {before}, Dup IDs in df: {dup_in_df}")

df_clean = df[~df["id"].isin(dup_ids)]
print(f"After: {len(df_clean)}")

# Write
cols = ["title","date","summary","root_cause","consequence","accident_type",
        "related_chemicals","related_equipment","source_url","location"]
with open("data/release/accidents.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(cols)
    for _, r in df_clean.iterrows():
        w.writerow([str(r.get(c, "") or "") for c in cols])

# Weather
wdf = pd.read_sql("SELECT * FROM weather_records", conn)
wdf.to_csv("data/release/weather_records.csv", index=False)

# Chemicals
cdf = pd.read_sql("SELECT chemical_name,cas_number,iupac_name,molecular_weight,flash_point,lower_explosion_limit,toxicity_class FROM chemical_properties", conn)
cdf.to_csv("data/release/chemical_properties.csv", index=False)

# Update DATASET_CARD
with open("data/release/DATASET_CARD.md", "r", encoding="utf-8") as f:
    card = f.read()
card = card.replace("1,579 起事故", f"{len(df_clean)} 起事故")
card = card.replace("1,579 条", f"{len(df_clean)} 条")
with open("data/release/DATASET_CARD.md", "w", encoding="utf-8") as f:
    f.write(card)

print(f"Release CSVs exported: accidents={len(df_clean)}, weather={len(wdf)}, chem={len(cdf)}")
conn.close()
