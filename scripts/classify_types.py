"""一次性事故类型分类，写入SQLite"""
import sqlite3
DB = "data/processed/chemsafe.db"

TYPE_KW = {
    "爆炸": ["爆炸", "爆燃", "闪爆", "爆轰"],
    "中毒窒息": ["中毒", "窒息"],
    "火灾": ["火灾", "起火", "燃烧"],
    "泄漏": ["泄漏", "泄露", "逸散"],
    "坍塌": ["坍塌", "倒塌"],
}

conn = sqlite3.connect(DB)

# Add column if not exists
try:
    conn.execute("ALTER TABLE accidents ADD COLUMN accident_type VARCHAR(20)")
    print("Added accident_type column")
except sqlite3.OperationalError:
    print("accident_type column already exists")

# Classify all
rows = conn.execute("SELECT id, title, root_cause FROM accidents WHERE accident_type IS NULL OR accident_type = ''").fetchall()
print(f"待分类: {len(rows)}")

updated = 0
for rid, title, root_cause in rows:
    txt = f"{title or ''} {root_cause or ''}"
    atype = "其他"
    for t, kws in TYPE_KW.items():
        if any(kw in txt for kw in kws):
            atype = t; break
    conn.execute("UPDATE accidents SET accident_type = ? WHERE id = ?", (atype, rid))
    updated += 1

conn.commit()

# Verify
r = conn.execute("SELECT accident_type, count(*) FROM accidents GROUP BY accident_type ORDER BY 2 DESC").fetchall()
print("分类结果:")
for t, c in r:
    print(f"  {t}: {c}")

conn.close()
print(f"完成: {updated} 条")
