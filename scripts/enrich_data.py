"""
数据充实脚本：为已采集的事故报告补充化学品物性与气象数据。

运行方式:
    python scripts/enrich_data.py

流程:
    1. 从 SQLite 事故表中读取已抽取的化学品列表
    2. 对缺物性的化学品调用 PubChem API 补充
    3. 对事故补充对应时间地点的气象数据
    4. 将化学品物性写入 SQLite + Neo4j
"""
import sys, io, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("enrich")

logging.getLogger("urllib3").setLevel(logging.WARNING)


def main():
    logger.info("=" * 60)
    logger.info("  ChemSafe-KG 数据充实")
    logger.info("=" * 60)

    # ── 1. 化学品物性充实 ──
    logger.info("\n[1/3] 化学品物性采集...")
    from src.acquisition.chemical_api import ChemicalPropertyFetcher

    fetcher = ChemicalPropertyFetcher()
    chem_df = fetcher.build_property_table()

    if not chem_df.empty:
        # 写入 SQLite
        from config.database import SessionLocal, init_relational_db
        from src.storage.relational_db import ChemicalProperty
        
        init_relational_db()
        session = SessionLocal()
        try:
            for _, row in chem_df.iterrows():
                # 尝试更新或插入
                existing = session.query(ChemicalProperty).filter_by(
                    chemical_name=row.get("chemical_name", "")
                ).first()
                if not existing:
                    record = ChemicalProperty(
                        chemical_name=row.get("chemical_name", ""),
                        cas_number=row.get("cas_number", ""),
                        boiling_point=row.get("BoilingPoint"),
                        flash_point=row.get("FlashPoint"),
                    )
                    session.add(record)
            session.commit()
            logger.info(f"  化学品物性: {len(chem_df)} 条写入 SQLite")
        except Exception as e:
            session.rollback()
            logger.warning(f"  化学品写入失败: {e}")
        finally:
            session.close()

        # 写入 Neo4j Material 节点
        try:
            from src.storage.neo4j_client import Neo4jClient
            from src.preprocessing.data_merger import DataMerger
            neo4j = Neo4jClient()
            neo4j.connect()
            if neo4j.graph is not None:
                merger = DataMerger()
                linked = merger.link_accident_nodes_to_chemicals(neo4j, chem_df)
                logger.info(f"  Neo4j 化学品属性: {linked} 个节点已充实")
        except Exception as e:
            logger.warning(f"  Neo4j 化学品充实失败: {e}")

        # 存为 CSV（供 DataMerger 使用）
        csv_path = Path("data/external/chemical_properties.csv")
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        chem_df.to_csv(csv_path, index=False)
        logger.info(f"  化学品物性已保存: {csv_path}")
    else:
        logger.warning("  化学品物性采集失败（网络问题或 PubChem 不可达）")

    # ── 2. 气象数据采集 ──
    logger.info("\n[2/3] 气象数据采集...")
    try:
        from config.database import engine
        import pandas as pd
        df = pd.read_sql("SELECT DISTINCT location, date FROM accidents WHERE date IS NOT NULL LIMIT 20", engine)
        
        if not df.empty:
            from src.acquisition.weather_fetcher import WeatherDataFetcher
            weather = WeatherDataFetcher()
            weather_records = []

            for _, row in df.iterrows():
                loc = str(row.get("location", ""))
                date_val = row.get("date")
                if not loc or not date_val:
                    continue
                if isinstance(date_val, str):
                    from datetime import datetime
                    try:
                        date_val = datetime.strptime(date_val, "%Y-%m-%d")
                    except ValueError:
                        continue

                try:
                    result = weather.fetch_weather_by_location(
                        location=loc,
                        date=date_val,
                    )
                    if result:
                        result["location"] = loc
                        weather_records.append(result)
                except Exception:
                    pass

            if weather_records:
                weather_df = pd.DataFrame(weather_records)
                w_path = Path("data/external/weather_data.csv")
                weather_df.to_csv(w_path, index=False)
                logger.info(f"  气象数据: {len(weather_records)} 条记录已保存至 {w_path}")
            else:
                logger.warning("  气象数据采集无结果")
        else:
            logger.warning("  无可用日期数据，跳过气象采集")
    except Exception as e:
        logger.warning(f"  气象数据采集失败: {e}")

    # ── 3. 统一融合视图 ──
    logger.info("\n[3/3] 构建统一融合视图...")
    try:
        from config.database import engine
        import pandas as pd
        from src.preprocessing.data_merger import DataMerger

        accidents_df = pd.read_sql("SELECT * FROM accidents", engine)
        chemicals_df = pd.read_csv("data/external/chemical_properties.csv") if Path("data/external/chemical_properties.csv").exists() else pd.DataFrame()
        weather_df = pd.read_csv("data/external/weather_data.csv") if Path("data/external/weather_data.csv").exists() else pd.DataFrame()

        merger = DataMerger()
        unified = merger.build_unified_view(accidents_df, chemicals_df, weather_df)

        # 保存统一视图
        unified.to_csv("data/processed/unified_view.csv", index=False)
        summary = merger.get_fusion_summary(unified)
        logger.info(f"  统一视图: {summary['total_rows']} 行, {summary['total_columns']} 列")
        logger.info(f"  化学品覆盖率: {summary.get('chemical_coverage_pct', 0)}%")
        logger.info(f"  气象覆盖率: {summary.get('weather_coverage_pct', 0)}%")
    except Exception as e:
        logger.warning(f"  统一视图构建失败: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("  数据充实完成!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
