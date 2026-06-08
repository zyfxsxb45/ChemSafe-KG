"""
source_url 格式统一脚本 — 将多版本残留格式统一为 mem: / 微信: 前缀

当前混杂格式:
  - "mem:xxx.txt"        → 保留
  - "爬虫:xxx.txt"       → "mem:xxx.txt"
  - "微信:xxx.txt"       → 保留
  - "wechat:ciedu"       → "微信:unknown.txt"
  - "wechat:xxx.txt"     → "微信:xxx.txt"
  - "mem.gov.cn"         → "mem:unknown.txt"
  - "微信:xxx"           → 保留

运行: python scripts/normalize_source_url.py
"""
import os, sys, re, logging
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("normalize")

import sqlite3

DB_PATH = "data/processed/chemsafe.db"


def normalize(url: str) -> str:
    """标准化 source_url"""
    if not url:
        return "mem:unknown.txt"

    url = url.strip()

    # 已经是标准格式
    if url.startswith("mem:") or url.startswith("微信:"):
        return url

    # "爬虫:xxx" → "mem:xxx"
    if url.startswith("爬虫:"):
        return "mem:" + url[3:]

    # "wechat:xxx" → "微信:xxx"
    if url.lower().startswith("wechat:"):
        rest = url[7:]
        if rest == "ciedu":
            rest = "unknown.txt"
        return "微信:" + rest

    # "mem.gov.cn" → "mem:unknown.txt"
    if "mem.gov.cn" in url:
        return "mem:unknown.txt"

    # 兜底: 尝试提取文件名
    return f"mem:{url[-80:] if len(url) > 80 else url}"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT id, source_url FROM accidents").fetchall()
    logger.info(f"总记录: {len(rows)}")

    # 统计当前分布
    from collections import Counter
    prefixes = Counter()
    for r in rows:
        url = r["source_url"] or ""
        prefix = url.split(":")[0] if ":" in url else url[:20]
        prefixes[prefix] += 1

    logger.info("当前 source_url 前缀分布:")
    for p, c in prefixes.most_common():
        logger.info(f"  {p}: {c}")

    # 执行标准化
    updated = 0
    for r in rows:
        old = r["source_url"] or ""
        new = normalize(old)
        if old != new:
            conn.execute("UPDATE accidents SET source_url = ? WHERE id = ?", (new, r["id"]))
            updated += 1

    conn.commit()

    # 验证结果
    rows2 = conn.execute("SELECT source_url FROM accidents").fetchall()
    prefixes2 = Counter()
    for r in rows2:
        url = r["source_url"] or ""
        prefix = url.split(":")[0] if ":" in url else url[:20]
        prefixes2[prefix] += 1

    logger.info(f"\n标准化后 source_url 前缀分布:")
    for p, c in prefixes2.most_common():
        logger.info(f"  {p}: {c}")
    logger.info(f"共修改 {updated} 条")

    conn.close()


if __name__ == "__main__":
    main()
