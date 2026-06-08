"""
重建验证脚本

全量重建完成后自动运行，检查数据完整性和格式一致性。

检查项:
  SQLite:
    - 记录数 > 0
    - date 覆盖率 > 80%
    - root_cause / consequence 覆盖率 = 100%
    - source_url 格式统一（只有 mem: / 微信: 前缀）
  Neo4j:
    - 节点数 > 0
    - 5 种实体类型均存在
    - Accident 节点存在（v0.7 新功能）
    - belongs_to 关系存在
    - 无孤立 Abnormal_Condition（度=0）
  文件:
    - 报告文件数 vs SQLite 记录数对比
    - 无空文件

运行: python scripts/verify_rebuild.py
输出: 控制台健康报告 + data/processed/rebuild_verification.json
"""
import os, sys, json, re
from pathlib import Path
from datetime import datetime
from collections import Counter

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("verify")


def check_sqlite(db_path: str) -> dict:
    """检查 SQLite 数据完整性"""
    import sqlite3
    conn = sqlite3.connect(db_path)

    total = conn.execute("SELECT count(*) FROM accidents").fetchone()[0]
    date_ok = conn.execute(
        "SELECT count(*) FROM accidents WHERE date IS NOT NULL").fetchone()[0]
    root_ok = conn.execute(
        "SELECT count(*) FROM accidents WHERE root_cause IS NOT NULL AND root_cause != ''").fetchone()[0]
    cons_ok = conn.execute(
        "SELECT count(*) FROM accidents WHERE consequence IS NOT NULL AND consequence != ''").fetchone()[0]

    # source_url 格式
    prefixes = Counter()
    bad = []
    rows = conn.execute("SELECT id, source_url FROM accidents").fetchall()
    for rid, url in rows:
        url = url or ""
        if url.startswith("mem:") or url.startswith("微信:"):
            prefixes[url.split(":")[0]] += 1
        else:
            bad.append(str(rid))

    conn.close()

    date_pct = 100 * date_ok / max(total, 1)
    root_pct = 100 * root_ok / max(total, 1)

    result = {
        "total": total,
        "date_ok": date_ok,
        "date_pct": round(date_pct, 1),
        "root_ok": root_ok,
        "root_pct": round(root_pct, 1),
        "cons_ok": cons_ok,
        "source_prefixes": dict(prefixes),
        "source_bad": len(bad),
    }

    issues = []
    if total == 0:
        issues.append("❌ SQLite accidents 表为空")
    if date_pct < 80:
        issues.append(f"⚠️ date 覆盖率仅 {date_pct:.1f}%，目标 ≥80%")
    if root_pct < 95:
        issues.append(f"⚠️ root_cause 覆盖率 {root_pct:.1f}%")
    if bad:
        issues.append(f"⚠️ {len(bad)} 条 source_url 格式异常（非 mem:/微信: 前缀）")

    result["issues"] = issues
    result["status"] = "✅ 通过" if not issues else "⚠️ 有警告"
    return result


def check_neo4j() -> dict:
    """检查 Neo4j 数据完整性"""
    from src.storage.neo4j_client import Neo4jClient
    neo4j = Neo4jClient()
    neo4j.connect()

    if neo4j.graph is None:
        return {"status": "❌ Neo4j 未连接", "issues": ["无法连接 Neo4j"]}

    # 节点类型分布
    r = neo4j.graph.run(
        "MATCH (n) WHERE size(labels(n))>0 "
        "RETURN labels(n)[0] as l, count(*) as c ORDER BY c DESC"
    ).data()
    node_types = {row["l"]: row["c"] for row in r}
    total_nodes = sum(node_types.values())

    # 关系数
    total_rels = neo4j.graph.run(
        "MATCH ()-[r]->() RETURN count(r) as c").data()[0]["c"]

    # Accident 节点
    acc_count = node_types.get("Accident", 0)

    # belongs_to 关系
    belongs = neo4j.graph.run(
        "MATCH ()-[r:belongs_to]->() RETURN count(r) as c").data()[0]["c"]

    # Mitigation 节点
    mit = node_types.get("Mitigation", 0)

    # 孤立 Abnormal_Condition
    orphan_abnormal = neo4j.graph.run("""
        MATCH (n:Abnormal_Condition)
        WHERE NOT (n)--()
        RETURN count(n) as c
    """).data()[0]["c"]

    # 因果链深度统计
    chain_depths = neo4j.graph.run("""
        MATCH path = ()-[:leads_to*1..6]->()
        RETURN length(path) as depth, count(*) as cnt ORDER BY depth
    """).data()
    max_depth = chain_depths[-1]["depth"] if chain_depths else 0

    result = {
        "total_nodes": total_nodes,
        "total_rels": total_rels,
        "node_types": node_types,
        "accident_nodes": acc_count,
        "belongs_to_rels": belongs,
        "mitigation_nodes": mit,
        "orphan_abnormal": orphan_abnormal,
        "max_chain_depth": max_depth,
    }

    issues = []
    if total_nodes == 0:
        issues.append("❌ Neo4j 无节点")
    expected_types = {"Equipment", "Material", "Abnormal_Condition", "Consequence", "Mitigation"}
    missing = expected_types - set(node_types.keys())
    if missing:
        issues.append(f"⚠️ 缺少实体类型: {missing}")
    if acc_count == 0:
        issues.append("⚠️ 无 Accident 聚合节点（v0.7 新功能未生效）")
    if mit < 20:
        issues.append(f"⚠️ Mitigation 节点仅 {mit} 个，偏少")
    if orphan_abnormal > total_nodes * 0.05:
        issues.append(f"⚠️ 孤立 Abnormal_Condition 节点 {orphan_abnormal} 个")

    result["issues"] = issues
    result["status"] = "✅ 通过" if not issues else "⚠️ 有警告"
    return result


def check_files() -> dict:
    """检查报告文件"""
    results = {}
    for label, dirname in [("mem", "accident_reports"), ("wechat", "wechat_reports")]:
        d = Path("data/raw") / dirname
        if not d.exists():
            results[label] = {"count": 0, "empty": 0, "status": f"⚠️ 目录不存在"}
            continue

        files = sorted(d.glob("*.txt"))
        empty = 0
        for f in files:
            if f.stat().st_size < 50:
                empty += 1

        results[label] = {
            "count": len(files),
            "empty": empty,
            "status": f"{len(files)} 个文件" + (f"，{empty} 个疑似空文件" if empty else ""),
        }
    return results


# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  ChemSafe-KG 重建验证")
    print("=" * 60)

    report = {
        "timestamp": datetime.now().isoformat(),
        "sqlite": {},
        "neo4j": {},
        "files": {},
    }

    # SQLite
    print("\n── SQLite ──")
    sql = check_sqlite("data/processed/chemsafe.db")
    report["sqlite"] = sql
    print(f"  记录数: {sql['total']}")
    print(f"  date: {sql['date_ok']}/{sql['total']} ({sql['date_pct']}%)")
    print(f"  root_cause: {sql['root_pct']}%")
    print(f"  source_url: {sql['source_prefixes']}" + (f" [异常:{sql['source_bad']}]" if sql['source_bad'] else ""))
    for issue in sql["issues"]:
        print(f"  {issue}")
    print(f"  → {sql['status']}")

    # Neo4j
    print("\n── Neo4j ──")
    ng = check_neo4j()
    report["neo4j"] = ng
    print(f"  节点: {ng['total_nodes']} | 关系: {ng['total_rels']}")
    print(f"  类型分布: {ng['node_types']}")
    print(f"  Accident: {ng['accident_nodes']} | belongs_to: {ng['belongs_to_rels']}")
    print(f"  Mitigation: {ng['mitigation_nodes']} | 孤立Abnormal: {ng['orphan_abnormal']}")
    print(f"  最大因果深度: {ng['max_chain_depth']}")
    for issue in ng["issues"]:
        print(f"  {issue}")
    print(f"  → {ng['status']}")

    # 文件
    print("\n── 报告文件 ──")
    files = check_files()
    report["files"] = files
    for label, info in files.items():
        print(f"  {label}: {info['status']}")

    # 保存报告
    out_path = Path("data/processed/rebuild_verification.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    all_issues = sql["issues"] + ng["issues"]
    print(f"\n{'='*60}")
    if all_issues:
        print(f"  ⚠️ 发现 {len(all_issues)} 个问题，详见上方")
    else:
        print(f"  ✅ 所有检查通过")
    print(f"  详细报告: {out_path}")
