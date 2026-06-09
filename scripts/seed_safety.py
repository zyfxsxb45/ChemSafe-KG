"""手动填充化学品安全物性（闪点、爆炸极限等）"""
import sqlite3
DB = "data/processed/chemsafe.db"

# (chemical_name, flash_point_C, lower_explosion_limit_%, upper_explosion_limit_%, autoignition_temp_C, toxicity_class)
DATA = [
    ("硫化氢", None, 4.0, 46.0, 260, "剧毒"),
    ("氮气", None, None, None, None, "窒息性"),
    ("甲醇", 12, 6.0, 36.0, 464, "有毒"),
    ("氢气", None, 4.0, 75.0, 500, "易燃"),
    ("氯乙烯", -78, 3.6, 33.0, 472, "致癌"),
    ("液化石油气", -104, 1.8, 9.5, 450, "易燃"),
    ("甲苯", 4, 1.2, 7.0, 480, "有毒"),
    ("汽油", -43, 1.4, 7.6, 280, "易燃"),
    ("双氧水", None, None, None, None, "氧化性"),
    ("苯", -11, 1.2, 7.8, 498, "致癌"),
    ("液氨", None, 15.0, 28.0, 651, "有毒"),
    ("氯气", None, None, None, None, "剧毒"),
    ("一氧化碳", None, 12.5, 74.0, 609, "有毒"),
    ("丙烯腈", -1, 3.0, 17.0, 481, "有毒/致癌"),
    ("乙炔", None, 2.5, 80.0, 305, "易燃"),
    ("环氧乙烷", -29, 3.0, 100.0, 429, "有毒/致癌"),
    ("乙醇", 13, 3.3, 19.0, 363, "易燃"),
    ("苯酚", 79, 1.7, 8.6, 715, "有毒"),
    ("丙酮", -17, 2.5, 12.8, 465, "易燃"),
    ("甲醛", 50, 7.0, 73.0, 430, "有毒/致癌"),
    ("氢氧化钠", None, None, None, None, "腐蚀性"),
    ("盐酸", None, None, None, None, "腐蚀性"),
    ("硫酸", None, None, None, None, "腐蚀性"),
    ("硝酸", None, None, None, None, "腐蚀性/氧化性"),
    ("光气", None, None, None, None, "剧毒"),
    ("氰化氢", -18, 5.6, 40.0, 538, "剧毒"),
    ("丙烯", -108, 2.0, 11.0, 460, "易燃"),
    ("丁二烯", -85, 2.0, 12.0, 420, "易燃/致癌"),
    ("苯乙烯", 32, 1.1, 6.1, 490, "有毒"),
    ("二甲苯", 27, 1.1, 7.0, 463, "有毒"),
    ("乙烷", -135, 3.0, 12.5, 515, "易燃"),
    ("乙烯", -136, 2.7, 36.0, 490, "易燃"),
    ("硝基苯", 88, 1.8, 40.0, 480, "有毒"),
    ("苯胺", 70, 1.3, 11.0, 615, "有毒"),
    ("TDI", 127, 0.9, 9.5, 620, "有毒"),
    ("TNT", None, None, None, None, "爆炸性"),
    ("环氧丙烷", -37, 2.3, 36.0, 430, "易燃/致癌"),
    ("醋酸", 39, 4.0, 17.0, 463, "腐蚀性"),
    ("氢氟酸", None, None, None, None, "剧毒/腐蚀性"),
    ("硝酸铵", None, None, None, None, "爆炸性/氧化性"),
    ("二硫化碳", -30, 1.3, 50.0, 100, "有毒/易燃"),
    ("丙烷", -104, 2.1, 9.5, 450, "易燃"),
    ("甲烷", -188, 5.0, 15.0, 537, "易燃"),
    ("氨水", None, None, None, None, "腐蚀性"),
]

conn = sqlite3.connect(DB)
updated = 0
for name, fp, lel, uel, ait, tox in DATA:
    sets = []
    vals = []
    if fp is not None:
        sets.append("flash_point = ?"); vals.append(fp)
    if lel is not None:
        sets.append("lower_explosion_limit = ?"); vals.append(lel)
    if uel is not None:
        sets.append("upper_explosion_limit = ?"); vals.append(uel)
    if ait is not None:
        sets.append("autoignition_temp = ?"); vals.append(ait)
    if tox is not None:
        sets.append("toxicity_class = ?"); vals.append(tox)
    if sets:
        vals.append(name)
        conn.execute(f"UPDATE chemical_properties SET {', '.join(sets)} WHERE chemical_name = ?", vals)
        updated += 1

conn.commit()

# Check how many now have flash_point and lower_explosion_limit
fp = conn.execute("SELECT count(*) FROM chemical_properties WHERE flash_point IS NOT NULL").fetchone()[0]
lel = conn.execute("SELECT count(*) FROM chemical_properties WHERE lower_explosion_limit IS NOT NULL").fetchone()[0]
tox = conn.execute("SELECT count(*) FROM chemical_properties WHERE toxicity_class IS NOT NULL").fetchone()[0]
conn.close()

print(f"Updated: {updated}")
print(f"flash_point: {fp}, lower_explosion_limit: {lel}, toxicity_class: {tox}")
