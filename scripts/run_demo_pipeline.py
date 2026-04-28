"""
ChemSafe-KG 端到端演示流水线

用样本事故数据走通完整的流水线:
  样本文本 -> LLM 抽取 -> 三元组 -> Neo4j 写入 -> Cypher 检索 -> RAG 上下文 -> LLM 答案生成

运行方式:
    .venv/Scripts/python scripts/run_demo_pipeline.py

依赖: .env 中需配置 LLM_API_KEY, Neo4j 服务需运行
"""
import sys
import json
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("demo")

# 抑制过于冗长的日志
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Windows GBK 兼容
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# 样本事故数据
SAMPLE_ACCIDENTS = [
    {
        "title": "案例1: 某化工厂丙烯腈储罐爆炸事故",
        "text": (
            "2023年5月7日，某化工厂丙烯腈储罐区因冷却水循环泵故障，"
            "导致储罐温度持续上升。高温引发丙烯腈自聚放热反应，"
            "罐内压力急剧升高，最终储罐超压破裂，"
            "丙烯腈蒸气泄漏并遇静电火花发生爆炸。"
            "操作人员紧急启动泡沫灭火系统和罐区喷淋。"
        ),
    },
    {
        "title": "案例2: 某石化企业苯泄漏中毒事故",
        "text": (
            "2022年8月15日，某石化企业苯储罐出口法兰密封失效，"
            "导致苯大量泄漏，挥发形成高浓度苯蒸气云团。"
            "现场3名操作工未佩戴防毒面具，吸入高浓度苯蒸气后"
            "出现头晕、恶心症状，最终确诊为急性苯中毒。"
            "救援人员穿戴空气呼吸器关闭了泄漏阀门。"
        ),
    },
]

SAMPLE_QUESTIONS = [
    "冷却水循环泵故障如何导致丙烯腈储罐爆炸？",
    "苯泄漏为什么会造成人员中毒？",
]


def extract_entity_type_map(extraction_result: dict) -> dict:
    """
    从 LLM 抽取结果中提取 {实体名: 实体类型} 映射。

    extraction_result 的 event_chain 包含交替的实体定义和关系:
      {"entity": "冷却水循环泵", "type": "Equipment", ...}
      {"relation": "leads_to", "target": "..."}
    """
    type_map = {}
    for item in extraction_result.get("event_chain", []):
        if "entity" in item and "type" in item:
            type_map[item["entity"]] = item["type"]
        if "relation" in item and "target" in item:
            target = item["target"]
            if target not in type_map and "type" in item:
                type_map[target] = item.get("type", "Abnormal_Condition")
    return type_map


def run_demo():
    """运行端到端演示流水线"""
    print("=" * 65)
    print("  ChemSafe-KG 端到端流水线演示")
    print("=" * 65)

    # [1/6] 初始化模块
    print("\n[1/6] 初始化模块...")
    from src.extraction.entity_extractor import EntityExtractor
    from src.storage.neo4j_client import Neo4jClient
    from src.retrieval.causal_path_retriever import CausalPathRetriever
    from src.qa.answer_generator import AnswerGenerator

    extractor = EntityExtractor()
    neo4j = Neo4jClient()
    neo4j.connect()
    if neo4j.graph is None:
        print("[失败] Neo4j 连接失败，请检查服务是否运行")
        return

    retriever = CausalPathRetriever(neo4j)
    qa = AnswerGenerator()
    print("  [OK] 模块初始化完成")

    # [2/6] 清空图谱
    print("\n[2/6] 重置知识图谱...")
    before = neo4j.get_entity_count()
    if before > 0:
        neo4j.clear_all()
        print(f"  [清理] 已清除 {before} 个旧节点")
    else:
        print("  [OK] 图谱为空，无需清理")

    # [3/6] LLM 知识抽取
    print("\n[3/6] LLM 知识抽取...")
    all_triples = []
    all_type_maps = []

    for case in SAMPLE_ACCIDENTS:
        print(f"\n  --- {case['title']} ---")
        print(f"  原文: {case['text'][:60]}...")

        result = extractor.extract_from_text(case["text"])
        if not result:
            print("  [跳过] 抽取失败")
            continue

        type_map = extract_entity_type_map(result)
        all_type_maps.append(type_map)

        triples = extractor.convert_to_triples(result)
        all_triples.extend(triples)

        print(f"  实体类型: {set(type_map.values())}")
        print(f"  三元组: {triples}")

    if not all_triples:
        print("\n[终止] 未抽取到任何三元组")
        return

    # [4/6] 写入 Neo4j
    print(f"\n[4/6] 写入 Neo4j ({len(all_triples)} 条三元组)...")
    merged_type_map = {}
    for tm in all_type_maps:
        merged_type_map.update(tm)

    neo4j.batch_create_triples(all_triples, entity_type_map=merged_type_map)

    node_cnt = neo4j.get_entity_count()
    rel_cnt = neo4j.get_relation_count()
    print(f"  [OK] 写入完成: {node_cnt} 节点, {rel_cnt} 关系")

    entities = neo4j.get_all_entity_names()
    print(f"  图谱实体: {entities}")

    # [5/6] 因果路径检索
    print(f"\n[5/6] 因果路径检索...")
    contexts = []

    for question in SAMPLE_QUESTIONS:
        print(f"\n  Q: {question}")

        # 匹配实体: 按关键词密度 + 精确性排序
        # 得分 = 关键词命中数 + 0.01 * 关键词密度 (打破平局)
        import jieba
        words = [w for w in jieba.lcut(question) if len(w) >= 2]
        entity_scores = []
        for e in entities:
            matches = [w for w in words if w in e]
            if matches:
                density = len(matches) / max(len(e), 1)
                entity_scores.append((e, len(matches) + density * 0.1))
        entity_scores.sort(key=lambda x: -x[1])
        matched_entities = [e for e, _ in entity_scores]
        print(f"     分词: {words}")
        print(f"     匹配实体(按相关度): {matched_entities}")

        if not matched_entities:
            context = "未检索到与问题相关的因果路径。"
        else:
            paths = retriever.retrieve(matched_entities[0], max_depth=4)
            context = retriever.format_context(paths)
            print(f"     因果路径:")
            for line in context.split("\n"):
                print(f"       {line}")
        contexts.append(context)

    # [6/6] LLM 答案生成
    print(f"\n[6/6] LLM 答案生成 (Graph RAG)...")
    for i, question in enumerate(SAMPLE_QUESTIONS):
        print(f"\n  Q: {question}")
        answer = qa.generate(question, contexts[i])
        print(f"  A:")
        for line in answer.strip().split("\n"):
            print(f"    {line}")

    # 汇总
    print("\n" + "=" * 65)
    print("  流水线演示完成!")
    print(f"  Neo4j: {neo4j.get_entity_count()} 节点, {neo4j.get_relation_count()} 关系")
    print("=" * 65)
    print("\n启动 Streamlit 问答界面:")
    print("  streamlit run app.py")


if __name__ == "__main__":
    run_demo()
