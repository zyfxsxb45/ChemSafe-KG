"""
跨源数据链接模块 v0.5

实现知识图谱 (Neo4j) 与关系数据库 (SQLite) 之间的双向链接、属性同步和一致性校验。

核心功能:
  1. 化学品物性 → Neo4j Material 节点属性同步
  2. SQLite 事故记录 → Neo4j Accident 节点创建与关联
  3. 双存储一致性校验（Neo4j 实体 vs SQLite 记录）
  4. 跨源统计（图密度 + 表完整率联合评估）
"""
import logging
from typing import Dict, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class DataLinker:
    """跨源数据链接器"""

    # ═══════════════════════════════════════════════════════════════
    #  化学品物性 → Neo4j Material 节点
    # ═══════════════════════════════════════════════════════════════
    def link_chemicals_to_graph(
        self,
        neo4j_client,
        db_session,
    ) -> Dict:
        """
        将 SQLite chemical_properties 的物性同步到 Neo4j Material 节点。

        策略: 按 chemical_name 匹配 Neo4j 中的 Material 节点，
              将分子量、CAS、IUPAC 名等属性写入节点。
        """
        if neo4j_client.graph is None:
            return {"error": "Neo4j not connected"}

        from src.storage.relational_db import ChemicalProperty

        stats = {"total": 0, "synced": 0, "new_nodes": 0, "errors": 0}

        try:
            chemicals = db_session.query(ChemicalProperty).all()
            stats["total"] = len(chemicals)

            for chem in chemicals:
                if not chem.chemical_name:
                    continue

                props = {}
                if chem.cas_number:
                    props["cas_number"] = chem.cas_number
                if chem.molecular_weight:
                    props["molecular_weight"] = chem.molecular_weight
                if chem.iupac_name:
                    props["iupac_name"] = chem.iupac_name

                if not props:
                    continue

                # 尝试更新现有 Material 节点
                set_clauses = ", ".join(f"n.{k} = ${k}" for k in props)
                result = neo4j_client.graph.run(
                    f"MATCH (n:Material {{name: $name}}) SET {set_clauses} "
                    "RETURN n.name AS name",
                    name=chem.chemical_name,
                    **props,
                ).data()

                if result:
                    stats["synced"] += 1
                else:
                    # 创建新 Material 节点
                    neo4j_client.graph.run(
                        "CREATE (n:Material {name: $name}) SET n += $props",
                        name=chem.chemical_name,
                        props=props,
                    )
                    stats["new_nodes"] += 1

            logger.info(
                f"化学品链接完成: {stats['synced']} 同步, "
                f"{stats['new_nodes']} 新建, {stats['errors']} 错误"
            )

        except Exception as e:
            logger.error(f"化学品链接失败: {e}")
            stats["errors"] += 1

        return stats

    # ═══════════════════════════════════════════════════════════════
    #  SQLite 事故 → Neo4j Accident 节点
    # ═══════════════════════════════════════════════════════════════
    def link_accidents_to_graph(
        self,
        neo4j_client,
        db_session,
        max_accidents: int = 50,
    ) -> Dict:
        """
        为 SQLite 中的事故记录在 Neo4j 中创建对应的 Accident 节点，
        并关联到已有的实体节点。

        策略:
          1. 为每个事故创建 Accident 节点 (title + date + root_cause)
          2. 按 related_chemicals 创建 belongs_to 关系到 Material 节点
          3. 按 related_equipment 创建 belongs_to 关系到 Equipment 节点
        """
        if neo4j_client.graph is None:
            return {"error": "Neo4j not connected"}

        from src.storage.relational_db import AccidentRecord

        stats = {"total": 0, "created": 0, "skipped": 0, "linked_chems": 0, "linked_equip": 0}

        try:
            accidents = db_session.query(AccidentRecord).limit(max_accidents).all()
            stats["total"] = len(accidents)

            for acc in accidents:
                # 检查是否已存在
                existing = neo4j_client.graph.run(
                    "MATCH (a:Accident {title: $title}) RETURN a LIMIT 1",
                    title=acc.title,
                ).data()

                if existing:
                    stats["skipped"] += 1
                    continue

                # 创建 Accident 节点
                neo4j_client.graph.run(
                    "CREATE (a:Accident {title: $title, date: $date, "
                    "root_cause: $root_cause, consequence: $consequence})",
                    title=acc.title,
                    date=str(acc.date) if acc.date else "",
                    root_cause=acc.root_cause or "",
                    consequence=acc.consequence or "",
                )
                stats["created"] += 1

                # 关联化学品
                if acc.related_chemicals:
                    for chem in acc.related_chemicals.split(","):
                        chem = chem.strip()
                        if not chem:
                            continue
                        result = neo4j_client.graph.run(
                            "MATCH (a:Accident {title: $title}) "
                            "MATCH (m:Material {name: $chem}) "
                            "MERGE (a)-[:involves]->(m)",
                            title=acc.title, chem=chem,
                        ).data()
                        if result is not None:
                            stats["linked_chems"] += 1

                # 关联设备
                if acc.related_equipment:
                    for eq in acc.related_equipment.split(","):
                        eq = eq.strip()
                        if not eq:
                            continue
                        neo4j_client.graph.run(
                            "MATCH (a:Accident {title: $title}) "
                            "MATCH (e:Equipment {name: $eq}) "
                            "MERGE (a)-[:involves]->(e)",
                            title=acc.title, eq=eq,
                        )
                        stats["linked_equip"] += 1

            logger.info(
                f"事故链接完成: {stats['created']} 新建, "
                f"{stats['skipped']} 跳过, "
                f"{stats['linked_chems']} 化学品关联, "
                f"{stats['linked_equip']} 设备关联"
            )

        except Exception as e:
            logger.error(f"事故链接失败: {e}")

        return stats

    # ═══════════════════════════════════════════════════════════════
    #  双存储一致性校验
    # ═══════════════════════════════════════════════════════════════
    def verify_consistency(
        self,
        neo4j_client,
        db_session,
    ) -> Dict:
        """
        校验 Neo4j 和 SQLite 之间的数据一致性。

        检查项:
          1. Neo4j 实体数 vs SQLite 记录数
          2. Material 节点是否都有对应的 chemical_properties 记录
          3. 孤立的 Neo4j 节点（无 SQLite 来源）
        """
        if neo4j_client.graph is None:
            return {"error": "Neo4j not connected"}

        from src.storage.relational_db import AccidentRecord, ChemicalProperty

        report = {}

        # 节点 vs 记录数量对比
        neo4j_nodes = neo4j_client.get_entity_count()
        sql_accidents = db_session.query(AccidentRecord).count()
        sql_chemicals = db_session.query(ChemicalProperty).count()
        report["neo4j_nodes"] = neo4j_nodes
        report["sqlite_accidents"] = sql_accidents
        report["sqlite_chemicals"] = sql_chemicals

        # Material 节点覆盖率
        if neo4j_client.graph:
            kg_materials = neo4j_client.graph.run(
                "MATCH (m:Material) WHERE m.name IS NOT NULL RETURN m.name"
            ).data()
            kg_material_names = {r["m.name"] for r in kg_materials}

            sql_material_names = {
                r[0] for r in db_session.query(ChemicalProperty.chemical_name).all()
            }

            report["kg_material_count"] = len(kg_material_names)
            report["sql_material_count"] = len(sql_material_names)
            report["materials_in_both"] = len(kg_material_names & sql_material_names)
            report["materials_only_in_kg"] = len(kg_material_names - sql_material_names)
            report["materials_only_in_sql"] = len(sql_material_names - kg_material_names)

            # 孤立节点（度=0 的节点可能是 LLM 抽取噪声）
            orphan_count = neo4j_client.graph.run(
                "MATCH (n) WHERE NOT (n)--() AND size(labels(n)) > 0 "
                "AND labels(n)[0] IN ['Equipment','Material','Abnormal_Condition','Consequence','Mitigation'] "
                "RETURN count(n) AS c"
            ).data()[0]["c"]
            report["orphan_nodes"] = orphan_count

        logger.info(f"一致性校验: {report}")
        return report

    # ═══════════════════════════════════════════════════════════════
    #  跨源统计
    # ═══════════════════════════════════════════════════════════════
    def cross_source_stats(
        self,
        neo4j_client,
        db_session,
    ) -> Dict:
        """生成双存储联合统计"""
        from src.storage.relational_db import AccidentRecord

        stats = {}

        # Neo4j
        if neo4j_client.graph:
            stats["neo4j_nodes"] = neo4j_client.get_entity_count()
            stats["neo4j_rels"] = neo4j_client.get_relation_count()
            # 图密度
            n = max(stats["neo4j_nodes"], 1)
            max_edges = n * (n - 1)
            stats["graph_density"] = round(stats["neo4j_rels"] / max(max_edges, 1), 6)
            # 平均度
            stats["avg_degree"] = round(stats["neo4j_rels"] / n, 1)

        # SQLite
        stats["sqlite_accidents"] = db_session.query(AccidentRecord).count()
        stats["sqlite_accidents_with_chemicals"] = db_session.query(AccidentRecord).filter(
            AccidentRecord.related_chemicals.isnot(None),
            AccidentRecord.related_chemicals != "",
        ).count()

        # 跨源比率
        if stats.get("neo4j_nodes", 0) > 0:
            stats["nodes_per_accident"] = round(
                stats["neo4j_nodes"] / max(stats["sqlite_accidents"], 1), 1
            )

        logger.info(f"跨源统计: {stats}")
        return stats
