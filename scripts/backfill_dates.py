"""
日期列回填脚本 — 从 summary 文本中提取日期写入 accidents.date

现有 1,326 条记录中 date 全为 NULL，但 1,025 条的 summary 包含日期信息。
本脚本从 summary 和 source_url（文件名）中尝试提取日期并回填。

运行: python scripts/backfill_dates.py
"""
import os, sys, re, logging
from pathlib import Path
from datetime import datetime

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("backfill")

import sqlite3

DB_PATH = "data/processed/chemsafe.db"

# ── 日期提取策略（按优先级） ─────────────────────────────────────────
# 1. summary 中的 "YYYY年MM月DD日" 格式
# 2. summary 中的 "YYYY-MM-DD" 格式
# 3. source_url 文件名中的日期（如 "5·11" → 需要年份推断）
# 4. title 中的年份推断

YMD_RE = re.compile(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日')
YMD_DASH_RE = re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})')
YEAR_RE = re.compile(r'(\d{4})\s*年')


def extract_date(title: str, summary: str, source_url: str) -> str | None:
    """尝试提取日期，返回 'YYYY-MM-DD' 或 None"""
    text = f"{title} {summary}"

    # 策略1: YYYY年MM月DD日
    m = YMD_RE.search(text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1940 <= y <= 2026 and 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"

    # 策略2: YYYY-MM-DD
    m = YMD_DASH_RE.search(text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1940 <= y <= 2026 and 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"

    # 策略3: 从文件名推断（如 "2020-05-07" 出现在 source_url）
    m = YMD_DASH_RE.search(source_url)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1940 <= y <= 2026 and 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"

    # 策略4: 只提取年份（设为该年1月1日，标记为近似）
    m = YEAR_RE.search(text)
    if m:
        y = int(m.group(1))
        if 1940 <= y <= 2026:
            return f"{y:04d}-01-01"

    return None


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT count(*) FROM accidents").fetchone()[0]
    null_count = conn.execute("SELECT count(*) FROM accidents WHERE date IS NULL").fetchone()[0]

    logger.info(f"总记录: {total}, date 为 NULL: {null_count}")

    if null_count == 0:
        logger.info("没有需要回填的记录")
        conn.close()
        return

    rows = conn.execute(
        "SELECT id, title, summary, source_url FROM accidents WHERE date IS NULL"
    ).fetchall()

    updated = 0
    year_only = 0
    failed = 0

    for row in rows:
        date_str = extract_date(
            row["title"] or "",
            row["summary"] or "",
            row["source_url"] or "",
        )
        if date_str:
            conn.execute("UPDATE accidents SET date = ? WHERE id = ?", (date_str, row["id"]))
            updated += 1
            if date_str.endswith("-01-01"):
                year_only += 1
        else:
            failed += 1

    conn.commit()
    conn.close()

    logger.info(f"回填完成: {updated} 条成功（其中 {year_only} 条仅有年份）, {failed} 条失败")
    logger.info(f"覆盖率: {updated}/{null_count} ({100*updated/max(null_count,1):.1f}%)")


if __name__ == "__main__":
    main()
