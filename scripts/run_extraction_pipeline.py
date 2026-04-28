"""
知识抽取流水线运行脚本

直接运行 LLM 驱动的知识抽取流水线: 文本 → 三元组 → Neo4j。

使用方式:
    python scripts/run_extraction_pipeline.py --input data/processed/cleaned_reports

TODO [完善]:
  1. 需要 LLM API Key 配置
  2. 需要清洗后的报告文本
  3. 需要 Neo4j 服务
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("extraction_pipeline")


def run(input_dir: str):
    """
    运行知识抽取流水线。

    流程:
    1. 加载清洗后的报告文本
    2. 逐段调用 LLM 抽取实体关系
    3. 验证和清洗抽取结果
    4. 转换为三元组
    5. 写入 Neo4j
    """
    logger.info("=" * 50)
    logger.info("LLM 知识抽取流水线")
    logger.info("=" * 50)

    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error(f"输入目录不存在: {input_path}")
        return

    # TODO [完善]: 实现完整的抽取流水线
    # from src.extraction.entity_extractor import EntityExtractor
    # from src.extraction.result_validator import ResultValidator
    # from src.storage.neo4j_client import Neo4jClient
    #
    # extractor = EntityExtractor()
    # validator = ResultValidator()
    # neo4j = Neo4jClient()
    #
    # for report_file in input_path.glob("*.txt"):
    #     text = report_file.read_text(encoding="utf-8")
    #     result = extractor.extract_from_text(text)
    #     if validator.validate_structure(result):
    #         triples = extractor.convert_to_triples(result)
    #         neo4j.batch_create_triples(triples, source_report=report_file.name)

    logger.warning("抽取流水线逻辑尚未实现。")
    logger.warning("请在 src/extraction/ 中填充 LLM 调用逻辑。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM 知识抽取流水线")
    parser.add_argument(
        "--input",
        default="data/processed/cleaned_reports",
        help="清洗后的报告文本目录",
    )
    args = parser.parse_args()
    run(args.input)
