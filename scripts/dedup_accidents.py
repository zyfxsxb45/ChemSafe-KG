"""
事故去重 v5 — 极严格：仅标题相似度>95%（标点差异）
保守估计，避免误删
"""
import sqlite3, difflib, json, re
from collections import defaultdict
import pandas as pd

DB = "data/processed/chemsafe.db"
conn = sqlite3.connect(DB)
df = pd.read_sql("SELECT id, title, date, location, source_url FROM accidents", conn)

def is_compilation(t):
    t = str(t)
    if re.search(r'第\d+起', t) and ('危险化学品' in t or '事故盘点' in t or '化工事故' in t): return True
    if '历史上' in t and '危险化学品' in t: return True
    if '盘点' in t and ('化工事故' in t or '全国化工' in t): return True
    return False

# Only dedup non-compilation articles
non_comp = df[~df["title"].apply(is_compilation)]
print(f"非汇编文章: {len(non_comp)} / {len(df)}")

titles = non_comp["title"].tolist()
ids_list = non_comp["id"].tolist()

dedup = {}
for i in range(len(titles)):
    if ids_list[i] in dedup: continue
    for j in range(i+1, len(titles)):
        if ids_list[j] in dedup: continue
        ratio = difflib.SequenceMatcher(None, str(titles[i]), str(titles[j])).ratio()
        if ratio > 0.95:
            dedup[ids_list[j]] = ids_list[i]

# Show clusters
clusters = defaultdict(set)
for d, k in dedup.items():
    clusters[k].add(d); clusters[k].add(k)
clusters_list = [c for c in clusters.values() if len(c) >= 2]
clusters_list.sort(key=lambda c: -len(c))

print(f"去重簇: {len(clusters_list)} 组")
print(f"可去重: {len(dedup)} 条 ({len(dedup)/len(df)*100:.1f}%)")
print(f"去重后: {len(df) - len(dedup)} 条\n")

for i, c in enumerate(clusters_list[:12]):
    print(f"簇 {i+1} ({len(c)} 条):")
    for id_ in sorted(c):
        row = df[df["id"]==id_].iloc[0]
        mark = " ✓" if id_ not in dedup else " ✗"
        print(f"  #{id_}{mark} {row['title'][:100]}")
    print()

# Save
with open("data/processed/dedup_mapping.json", "w") as f:
    json.dump({int(k): int(v) for k, v in dedup.items()}, f)
df_clean = df[~df["id"].isin(dedup.keys())]
df_clean.to_csv("data/processed/accidents_deduped.csv", index=False)
print(f"已保存: dedup_mapping.json + accidents_deduped.csv ({len(df_clean)} 条)")

# Count true duplicates vs compilations
print(f"\n汇编文章: {df['title'].apply(is_compilation).sum()} 条(已保留,非重复)")
print(f"真正重复(>95%标题相似): {len(dedup)} 条")
conn.close()
