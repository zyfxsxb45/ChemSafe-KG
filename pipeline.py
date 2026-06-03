"""
ChemSafe-KG 主流水线编排器 v0.5

协调数据采集 → 预处理 → LLM 知识抽取 → 存储的完整流程。
支持分阶段执行、断点续跑和数据充实。

运行方式:
    python pipeline.py --stage all                    # 全流程
    python pipeline.py --stage acquisition            # 仅采集
    python pipeline.py --stage extraction             # 仅抽取
    python pipeline.py --stage enrich                 # 数据充实（化学品+气象）
    python pipeline.py --stage qa                     # 交互式问答
"""
import argparse
import logging
import json
import time
import re
import os
from pathlib import Path
from datetime import datetime

# 确保工作目录为项目根目录
os.chdir(Path(__file__).resolve().parent)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")

# 压低 LLM SDK 冗长日志
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class Pipeline:
    """ChemSafe-KG 主流水线"""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.checkpoint_file = Path("data/processed/pipeline_checkpoint.json")
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        # 统计
        self.stats = {
            "started": datetime.now().isoformat(),
            "stages": {},
        }

    # ═══════════════════════════════════════════════════════════════════
    #  阶段一: 数据采集
    # ═══════════════════════════════════════════════════════════════════
    def run_acquisition(self, max_reports: int = 100, sources: list[str] | None = None):
        """采集事故报告 + 化学品物性 + 气象数据"""
        logger.info("=" * 60)
        logger.info("  阶段一: 数据采集")
        logger.info("=" * 60)

        t0 = time.time()
        stats = {"reports": 0, "chemicals": 0, "weather": 0}

        # ── 1a. 爬取事故报告 ──
        if sources is None:
            sources = ["mem_warning"]
        logger.info(f"\n[采集] 事故报告: {sources}")

        from src.acquisition.report_crawler import ReportCrawler
        crawler = ReportCrawler()
        crawler.run(max_reports=max_reports, sources=sources)
        reports_dir = crawler.output_dir
        txt_files = sorted(reports_dir.glob("*.txt"))
        stats["reports"] = len(txt_files)
        logger.info(f"[采集] 事故报告: {stats['reports']} 份 (.txt)")

        # ── 1b. 化学品物性 ──
        logger.info("\n[采集] 化学品物性 (PubChem)...")
        try:
            from src.acquisition.chemical_api import ChemicalPropertyFetcher
            chem_fetcher = ChemicalPropertyFetcher()
            chem_df = chem_fetcher.build_property_table()
            if not chem_df.empty:
                csv_path = Path("data/external/chemical_properties.csv")
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                chem_df.to_csv(csv_path, index=False)
                stats["chemicals"] = len(chem_df)
                logger.info(f"[采集] 化学品物性: {stats['chemicals']} 种 → {csv_path}")
        except Exception as e:
            logger.warning(f"[采集] 化学品物性失败: {e}")

        # ── 1c. 气象数据(采样) ──
        logger.info("\n[采集] 气象数据 (Open-Meteo, 采样)...")
        try:
            from src.acquisition.weather_fetcher import WeatherDataFetcher
            weather = WeatherDataFetcher()
            # 采样最近3起事故获取天气
            records = []
            sample_files = txt_files[:3] if txt_files else []
            for f in sample_files:
                text = f.read_text(encoding="utf-8")
                date_m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
                loc_m = re.search(r"(?:河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|广西|四川|贵州|云南|陕西|甘肃|宁夏|内蒙古|新疆|北京|天津|上海|重庆)", text)
                if date_m:
                    try:
                        d = datetime.strptime(date_m.group(1), "%Y-%m-%d")
                        loc = loc_m.group(0) if loc_m else "北京"
                        result = weather.fetch_weather_by_location(loc, d)
                        if result:
                            records.append(result)
                    except ValueError:
                        pass
            if records:
                import pandas as pd
                pd.DataFrame(records).to_csv("data/external/weather_data.csv", index=False)
                stats["weather"] = len(records)
            logger.info(f"[采集] 气象数据: {stats['weather']} 条")
        except Exception as e:
            logger.warning(f"[采集] 气象数据失败: {e}")

        elapsed = time.time() - t0
        logger.info(f"\n[采集] 完成 (耗时 {elapsed:.0f}s): {stats}")
        self.stats["stages"]["acquisition"] = {**stats, "elapsed": round(elapsed, 1)}
        return stats

    # ═══════════════════════════════════════════════════════════════════
    #  阶段二: 知识抽取
    # ═══════════════════════════════════════════════════════════════════
    def run_extraction(self, input_dir: str = "data/raw/accident_reports",
                       batch_size: int = 5, max_files: int = 0):
        """LLM 知识抽取：报告文本 → 三元组 → Neo4j + SQLite"""
        logger.info("=" * 60)
        logger.info("  阶段二: LLM 知识抽取")
        logger.info("=" * 60)

        from scripts.run_extraction_pipeline import run
        run(input_dir=input_dir, batch_size=batch_size)
        # 脚本内部会输出详细统计

        # 补充统计
        try:
            from src.storage.neo4j_client import Neo4jClient
            neo4j = Neo4jClient()
            neo4j.connect()
            if neo4j.graph:
                nodes = neo4j.get_entity_count()
                rels = neo4j.get_relation_count()
                self.stats["stages"]["extraction"] = {"neo4j_nodes": nodes, "neo4j_rels": rels}
                logger.info(f"\n[抽取] Neo4j: {nodes} 节点, {rels} 关系")
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════
    #  阶段三: 数据充实
    # ═══════════════════════════════════════════════════════════════════
    def run_enrich(self):
        """补充化学品物性 + 气象数据到 SQLite 和 Neo4j"""
        logger.info("=" * 60)
        logger.info("  阶段三: 数据充实")
        logger.info("=" * 60)

        t0 = time.time()
        stats = {}

        # ── 化学品 → SQLite + Neo4j ──
        chem_csv = Path("data/external/chemical_properties.csv")
        if chem_csv.exists():
            import pandas as pd
            chem_df = pd.read_csv(chem_csv)
            logger.info(f"[充实] 化学品物性: {len(chem_df)} 种")

            # 写入 SQLite（字段映射: CSV列 → ORM列）
            try:
                from config.database import SessionLocal
                from src.storage.relational_db import ChemicalProperty
                session = SessionLocal()
                written = 0
                FIELD_MAP = {
                    'chemical_name': 'chemical_name',
                    'english_name': 'english_name',
                    'cas_number': 'cas_number',
                    'iupac_name': 'iupac_name',
                    'molecular_weight': 'molecular_weight',
                }
                for _, row in chem_df.iterrows():
                    cname = str(row.get("chemical_name", ""))
                    existing = session.query(ChemicalProperty).filter_by(chemical_name=cname).first()
                    if not existing:
                        kwargs = {}
                        for csv_col, orm_col in FIELD_MAP.items():
                            val = row.get(csv_col)
                            if pd.notna(val):
                                kwargs[orm_col] = val
                        if 'chemical_name' in kwargs:
                            session.add(ChemicalProperty(**kwargs))
                            written += 1
                session.commit()
                session.close()
                stats["chemicals_sqlite"] = written
                logger.info(f"[充实] SQLite 化学品: {written} 种新写入")
            except Exception as e:
                logger.warning(f"[充实] SQLite 化学品写入失败: {e}")

            # 写入 Neo4j
            try:
                from src.storage.neo4j_client import Neo4jClient
                from src.preprocessing.data_merger import DataMerger
                neo4j = Neo4jClient()
                neo4j.connect()
                if neo4j.graph:
                    merger = DataMerger()
                    linked = merger.link_accident_nodes_to_chemicals(neo4j, chem_df)
                    stats["chemicals_neo4j"] = linked
                    logger.info(f"[充实] Neo4j Material 节点: {linked} 个充实")
            except Exception as e:
                logger.warning(f"[充实] Neo4j 化学品充实失败: {e}")

        # ── 统一融合视图 ──
        try:
            from config.database import engine
            import pandas as pd
            from src.preprocessing.data_merger import DataMerger

            accidents_df = pd.read_sql("SELECT * FROM accidents", engine)
            chemicals_df = pd.read_csv(chem_csv) if chem_csv.exists() else pd.DataFrame()
            weather_df = pd.read_csv("data/external/weather_data.csv") if Path("data/external/weather_data.csv").exists() else pd.DataFrame()

            merger = DataMerger()
            unified = merger.build_unified_view(accidents_df, chemicals_df, weather_df)
            unified.to_csv("data/processed/unified_view.csv", index=False)

            fusion = merger.get_fusion_summary(unified)
            stats["unified_rows"] = fusion["total_rows"]
            stats["chem_coverage"] = f"{fusion.get('chemical_coverage_pct', 0)}%"
            stats["weather_coverage"] = f"{fusion.get('weather_coverage_pct', 0)}%"
            logger.info(f"[充实] 统一视图: {stats['unified_rows']} 行, 化学品覆盖 {stats['chem_coverage']}, 气象覆盖 {stats['weather_coverage']}")
        except Exception as e:
            logger.warning(f"[充实] 统一视图构建失败: {e}")

        elapsed = time.time() - t0
        logger.info(f"\n[充实] 完成 (耗时 {elapsed:.0f}s)")
        self.stats["stages"]["enrich"] = stats
        return stats

    # ═══════════════════════════════════════════════════════════════════
    #  阶段四: 问答验证
    # ═══════════════════════════════════════════════════════════════════
    def run_qa_test(self, questions: list[str] | None = None):
        """运行问答验证，测试知识图谱的问答质量"""
        logger.info("=" * 60)
        logger.info("  阶段四: 问答验证")
        logger.info("=" * 60)

        if questions is None:
            questions = [
                "冷却水循环泵故障如何导致储罐爆炸？",
                "苯泄漏为什么会造成人员中毒？",
                "反应釜超温超压通常由哪些因素引发？",
                "有限空间作业导致中毒窒息的常见原因是什么？",
            ]

        from src.storage.neo4j_client import Neo4jClient
        from src.retrieval.causal_path_retriever import CausalPathRetriever
        from src.qa.answer_generator import AnswerGenerator
        import jieba

        neo4j = Neo4jClient()
        neo4j.connect()
        if neo4j.graph is None:
            logger.error("Neo4j 未连接")
            return

        retriever = CausalPathRetriever(neo4j)
        qa = AnswerGenerator()
        entities = neo4j.get_all_entity_names()

        results = []
        for i, question in enumerate(questions, 1):
            logger.info(f"\n[QA {i}/{len(questions)}] {question}")

            # 实体匹配
            words = [w for w in jieba.lcut(question) if len(w) >= 2]
            scored = [(e, sum(1 for w in words if w in str(e))) for e in entities]
            matched = [e for e, s in sorted(scored, key=lambda x: -x[1]) if s > 0][:8]

            if not matched:
                logger.warning(f"  → 未匹配到实体")
                results.append({"question": question, "answer": "未找到相关实体", "paths": 0})
                continue

            # 检索因果路径
            all_paths = []
            for entity in matched[:5]:
                paths = retriever.retrieve(entity, max_depth=3)
                all_paths.extend(paths)

            # 去重排序
            all_paths.sort(key=lambda x: len(x.get("node_names", [])), reverse=True)
            # 简单去重
            seen_nodes = set()
            unique = []
            for p in all_paths:
                key = tuple(p.get("node_names", []))
                if key not in seen_nodes and len(key) >= 2:
                    seen_nodes.add(key)
                    unique.append(p)

            context = retriever.format_context(unique[:10])
            answer = qa.generate(question, context)

            results.append({
                "question": question,
                "answer": answer,
                "paths": len(unique),
                "top_entities": matched[:5],
            })

            # 打印摘要
            lines = answer.strip().split("\n")
            preview = "\n  ".join(lines[:5])
            logger.info(f"  → {len(unique)} 条路径, 回答预览:\n  {preview}")

        # 保存结果
        output = {"timestamp": datetime.now().isoformat(), "results": results}
        Path("data/processed/qa_results.json").write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"\n[QA] 结果已保存: data/processed/qa_results.json")
        return results

    # ═══════════════════════════════════════════════════════════════════
    #  主入口
    # ═══════════════════════════════════════════════════════════════════
    def run(self, stages: list[str], **kwargs):
        """运行指定阶段的流水线"""
        stage_map = {
            "acquisition": lambda: self.run_acquisition(
                max_reports=kwargs.get("max_reports", 100),
                sources=kwargs.get("sources"),
            ),
            "extraction": lambda: self.run_extraction(
                input_dir=kwargs.get("input_dir", "data/raw/accident_reports"),
                batch_size=kwargs.get("batch_size", 5),
            ),
            "enrich": self.run_enrich,
            "qa": lambda: self.run_qa_test(kwargs.get("questions")),
        }

        for stage in stages:
            if stage in stage_map:
                stage_map[stage]()
            else:
                logger.warning(f"未知阶段: {stage}")

        # 保存统计
        self.stats["completed"] = datetime.now().isoformat()
        self.checkpoint_file.write_text(
            json.dumps(self.stats, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"流水线完成，统计已保存: {self.checkpoint_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChemSafe-KG 数据流水线")
    parser.add_argument(
        "--stage", default="all",
        choices=["all", "acquisition", "extraction", "enrich", "qa"],
        help="运行阶段",
    )
    parser.add_argument("--max-reports", type=int, default=100,
                       help="采集事故报告上限")
    parser.add_argument("--batch-size", type=int, default=5,
                       help="LLM 抽取批量大小")
    parser.add_argument("--sources", nargs="*", default=None,
                       help="数据源列表 (默认: mem_warning)")
    args = parser.parse_args()

    if args.stage == "all":
        stages = ["acquisition", "extraction", "enrich", "qa"]
    else:
        stages = [args.stage]

    pipeline = Pipeline()
    pipeline.run(
        stages,
        max_reports=args.max_reports,
        batch_size=args.batch_size,
        sources=args.sources,
    )
