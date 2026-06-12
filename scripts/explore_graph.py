"""
Neo4j图谱探索 — 挖掘跨事故模式、枢纽节点、共性因果链
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.storage.neo4j_client import Neo4jClient
from collections import Counter, defaultdict

n = Neo4jClient(); n.connect()
print("Neo4j connected\n")

# ═══════════════════════════════════
# 1. 枢纽节点 — 度中心性 Top 20
# ═══════════════════════════════════
print("=" * 60)
print("1. 枢纽节点（度中心性 Top 20）")
print("=" * 60)
r = n.graph.run("""
    MATCH (n)
    WHERE n.name IS NOT NULL AND size(labels(n)) > 0
    WITH n, count { (n)--() } AS degree
    WHERE degree > 5
    RETURN labels(n)[0] AS type, n.name AS name, degree
    ORDER BY degree DESC LIMIT 20
""").data()
for row in r:
    print(f"  [{row['type']}] {row['name'][:50]:50s} degree={row['degree']}")

# ═══════════════════════════════════
# 2. 跨事故共性因果模式
# ═══════════════════════════════════
print("\n" + "=" * 60)
print("2. 跨事故共性因果模式（同一因果链出现在多起事故中）")
print("=" * 60)
r = n.graph.run("""
    MATCH (cause)-[:leads_to]->(effect)
    WHERE cause.name IS NOT NULL AND effect.name IS NOT NULL
    WITH cause.name + ' -> ' + effect.name AS pattern, 
         count(DISTINCT cause) AS freq
    WHERE freq >= 10
    RETURN pattern, freq
    ORDER BY freq DESC LIMIT 20
""").data()
for row in r:
    print(f"  [{row['freq']:3d}x] {row['pattern'][:80]}")

# ═══════════════════════════════════
# 3. 最频繁的2跳因果链
# ═══════════════════════════════════
print("\n" + "=" * 60)
print("3. 最频繁的2跳因果链（A→B→C模式）")
print("=" * 60)
r = n.graph.run("""
    MATCH path = (a)-[:leads_to]->(b)-[:leads_to]->(c)
    WHERE a.name IS NOT NULL AND b.name IS NOT NULL AND c.name IS NOT NULL
    WITH a.name + ' → ' + b.name + ' → ' + c.name AS chain, count(*) AS freq
    WHERE freq >= 5
    RETURN chain, freq ORDER BY freq DESC LIMIT 15
""").data()
for row in r:
    print(f"  [{row['freq']:2d}x] {row['chain'][:100]}")

# ═══════════════════════════════════
# 4. 化学品-后果关联：哪些化学品最常导致什么后果
# ═══════════════════════════════════
print("\n" + "=" * 60)
print("4. 化学品-后果强关联")
print("=" * 60)
r = n.graph.run("""
    MATCH (m:Material)-[:involves*0..1]-()-[*1..3]->(c:Consequence)
    WHERE m.name IS NOT NULL AND c.name IS NOT NULL
    WITH m.name AS chem, c.name AS consequence, count(*) AS cnt
    WHERE cnt >= 5
    RETURN chem, consequence, cnt ORDER BY cnt DESC LIMIT 15
""").data()
for row in r:
    print(f"  [{row['cnt']:3d}x] {row['chem'][:25]:25s} → {row['consequence'][:50]}")

# ═══════════════════════════════════
# 5. 设备故障的典型传播路径
# ═══════════════════════════════════
print("\n" + "=" * 60)
print("5. 设备故障→后果 典型路径")
print("=" * 60)
r = n.graph.run("""
    MATCH path = (e:Equipment)-[:leads_to*1..3]->(c:Consequence)
    WHERE e.name IS NOT NULL AND c.name IS NOT NULL
    WITH e.name AS equip, c.name AS conseq, count(*) AS cnt
    WHERE cnt >= 5
    RETURN equip, conseq, cnt ORDER BY cnt DESC LIMIT 15
""").data()
for row in r:
    print(f"  [{row['cnt']:3d}x] {row['equip'][:20]:20s} → {row['conseq'][:50]}")

# ═══════════════════════════════════
# 6. 孤立节点 — 没有出边也没有入边的节点
# ═══════════════════════════════════
print("\n" + "=" * 60)
print("6. 图谱质量：孤立节点统计")
print("=" * 60)
r = n.graph.run("""
    MATCH (n)
    WHERE count { (n)--() } = 0
    RETURN labels(n)[0] AS type, count(*) AS cnt
    ORDER BY cnt DESC
""").data()
for row in r:
    print(f"  [{row['type']}] 孤立节点: {row['cnt']}")

# ═══════════════════════════════════
# 7. 事故粒度：每起事故的平均因果链长度
# ═══════════════════════════════════
print("\n" + "=" * 60)
print("7. 因果链深度分布")
print("=" * 60)
r = n.graph.run("""
    MATCH path = (a:Accident)-[:belongs_to*0..1]-()-[r:leads_to*1..5]->()
    WITH a, max(length(path)) AS max_depth
    WHERE max_depth > 0
    RETURN 
        CASE WHEN max_depth <= 1 THEN '1跳' 
             WHEN max_depth <= 2 THEN '2跳' 
             WHEN max_depth <= 3 THEN '3跳' 
             ELSE '4+跳' END AS depth,
        count(*) AS cnt
    ORDER BY depth
""").data()
for row in r:
    print(f"  {row['depth']}: {row['cnt']} 起事故")

# ═══════════════════════════════════
# 8. 聚合统计
# ═══════════════════════════════════
print("\n" + "=" * 60)
print("8. 图谱全局统计")
print("=" * 60)
total_nodes = n.get_entity_count()
total_rels = n.get_relation_count()
r = n.graph.run("MATCH (n) RETURN labels(n)[0] AS t, count(*) AS c ORDER BY c DESC").data()
print(f"  总节点: {total_nodes}")
print(f"  总关系: {total_rels}")
for row in r: print(f"  [{row['t']}] {row['c']}")

print("\nDone.")
