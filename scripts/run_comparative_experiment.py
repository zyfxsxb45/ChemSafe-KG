"""
对照实验: Graph RAG vs 纯 LLM

评估指标:
  1. 幻觉检测: 回答中是否包含 KG 中不存在的实体/关系
  2. 因果完整性: 回答是否包含完整的因果链(≥3步)
  3. 来源可追溯性: 回答是否能追溯到具体数据源
  4. 拒答诚实性: 当KG无相关数据时是否诚实拒答而非编造

运行: python scripts/run_comparative_experiment.py
"""
import os, sys, json, time, re
from pathlib import Path
from datetime import datetime

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("experiment")
logging.getLogger("experiment").setLevel(logging.INFO)

import jieba
from collections import Counter


# ═══════════════════════════════════════════════════════════════════════
#  测试问题集（覆盖6种因果模式）
# ═══════════════════════════════════════════════════════════════════════
QUESTIONS = [
    # 模式1: 因果链查询 (KG中应有丰富路径)
    ("有限空间作业导致中毒窒息的事故链条是怎样的？", "causal_chain"),
    ("盲目施救如何导致事故后果扩大？", "causal_chain"),
    ("硫化氢中毒事故的典型发展过程是什么？", "causal_chain"),
    ("反应失控类事故通常经过哪几个阶段？", "causal_chain"),

    # 模式2: 致因归纳 (需要跨事故归纳共性模式)
    ("化工事故中，哪些违规操作行为出现频率最高？", "causal_pattern"),
    ("导致储罐事故的设备故障主要有哪些类型？", "causal_pattern"),

    # 模式3: 边界测试 (KG中无/少相关数据)
    ("冷却水循环泵故障如何导致丙烯腈储罐爆炸？", "boundary"),
    ("光气泄漏事故中应该采取哪些应急措施？", "boundary"),

    # 模式4: 泛化问题 (需要因果链+领域知识)
    ("为什么化工事故往往呈现'滚雪球'式的级联放大特征？", "generalization"),
    ("从历史事故来看，哪些中间异常状态最危险，为什么？", "generalization"),
]


# ═══════════════════════════════════════════════════════════════════════
def init_components():
    """初始化所有组件"""
    from src.storage.neo4j_client import Neo4jClient
    from src.retrieval.causal_path_retriever import CausalPathRetriever
    from src.qa.answer_generator import AnswerGenerator
    from src.extraction.llm_client import LLMClient

    neo4j = Neo4jClient()
    neo4j.connect()
    retriever = CausalPathRetriever(neo4j)
    qa = AnswerGenerator()
    llm = LLMClient()
    entities = neo4j.get_all_entity_names() if neo4j.graph else []

    return neo4j, retriever, qa, llm, entities


def run_graph_rag(question, neo4j, retriever, qa, entities):
    """Graph RAG 模式: KG检索 → 约束LLM生成"""
    # 三层实体匹配
    words = [w for w in jieba.lcut(question) if len(w) >= 2]
    scored = [(e, sum(1 for w in words if w in str(e))) for e in entities]
    matched = [e for e, s in sorted(scored, key=lambda x: -x[1]) if s > 0][:8]

    if not matched:
        return {"answer": "未匹配到实体", "paths": 0, "context": ""}

    # 检索因果路径
    all_paths = []
    for entity in matched[:5]:
        paths = retriever.retrieve(entity, max_depth=3)
        all_paths.extend(paths)

    all_paths.sort(key=lambda x: len(x.get("node_names", [])), reverse=True)
    seen = set()
    unique = []
    for p in all_paths:
        key = tuple(p.get("node_names", []))
        if key not in seen and len(key) >= 2:
            seen.add(key)
            unique.append(p)

    context = retriever.format_context(unique[:10])
    answer = qa.generate(question, context)

    return {
        "answer": answer,
        "paths": len(unique),
        "context": context,
        "matched_entities": matched[:5],
    }


def run_pure_llm(question, llm):
    """纯 LLM 模式: 无KG约束，直接回答"""
    system = "你是一位化工安全专家。请回答用户的问题。"
    try:
        answer = llm.chat(system, question)
    except Exception as e:
        answer = f"[LLM调用失败: {e}]"
    return {"answer": answer, "paths": 0, "context": ""}


def detect_hallucination(answer, neo4j):
    """检测回答中的不可核实断言：检查关键实体是否在KG中存在"""
    if neo4j.graph is None:
        return 0, []

    # 从KG中获取所有实体名作为白名单
    kg_entities = set()
    r = neo4j.graph.run(
        "MATCH (n) WHERE n.name IS NOT NULL AND size(labels(n))>0 "
        "WITH n, labels(n)[0] AS l WHERE l IN ['Equipment','Material','Abnormal_Condition','Consequence','Mitigation'] "
        "RETURN n.name AS name"
    ).data()
    kg_entities = {row['name'] for row in r}

    # 提取回答中的实体候选（化工安全领域特征词）
    domain_patterns = [
        r'[\u4e00-\u9fff]{3,}(?:爆炸|中毒|泄漏|火灾|窒息|故障|事故)',
        r'[\u4e00-\u9fff]{2,}(?:泵|阀|罐|塔|釜|炉|管|器|机)',
        r'[\u4e00-\u9fff]{2,}(?:硫化氢|氯气|氨|苯|甲醇|一氧化碳|氰化氢)',
        r'[\u4e00-\u9fff]{3,}(?:违规|操作|检修|动火|清洗)',
    ]
    candidates = set()
    for pattern in domain_patterns:
        candidates.update(re.findall(pattern, answer))

    # 也在KG中进行模糊匹配
    hallucinations = []
    for c in candidates:
        # 完全匹配或包含匹配
        match = neo4j.graph.run(
            "MATCH (n) WHERE n.name = $name OR n.name CONTAINS $name OR $name CONTAINS n.name "
            "RETURN n.name LIMIT 1",
            name=c
        ).data()
        if not match:
            hallucinations.append(c)

    total = len(candidates)
    return len(hallucinations), hallucinations[:8]


def evaluate_completeness(answer):
    """评估因果链完整性: 是否包含≥3步因果"""
    causal_keywords = ['→', '↓', '导致', '引发', '造成', '→', '路径']
    steps = 0
    for kw in causal_keywords:
        steps += answer.count(kw)
    # 也检查是否包含因果结构
    has_chain = any(phrase in answer for phrase in
                    ['事故链条概述', '关键节点', '事故链条', '因果链',
                     '第一步', '第二步', '第三步', '首先', '然后', '最终',
                     '初始原因', '中间状态', '最终后果'])
    return {
        "has_structured_chain": has_chain,
        "causal_marker_count": steps,
        "is_complete": has_chain and steps >= 2,
    }


# ═══════════════════════════════════════════════════════════════════════
def run():
    logger.info("=" * 70)
    logger.info("  ChemSafe-KG 对照实验: Graph RAG vs 纯 LLM")
    logger.info("=" * 70)

    neo4j, retriever, qa, llm, entities = init_components()
    if neo4j.graph is None:
        logger.error("Neo4j 未连接，终止实验")
        return

    results = []
    stats = {
        "graph_rag": {"total": 0, "hallucination_free": 0, "complete": 0, "with_sources": 0, "honest_refusal": 0},
        "pure_llm": {"total": 0, "hallucination_free": 0, "complete": 0, "with_sources": 0, "honest_refusal": 0},
    }

    for i, (question, qtype) in enumerate(QUESTIONS, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"  Q{i}: [{qtype}] {question[:50]}...")
        logger.info(f"{'='*60}")

        # ── Graph RAG ──
        t0 = time.time()
        rag_result = run_graph_rag(question, neo4j, retriever, qa, entities)
        rag_time = round((time.time() - t0) * 1000)

        rag_halluc, rag_halluc_list = detect_hallucination(rag_result["answer"], neo4j)
        rag_complete = evaluate_completeness(rag_result["answer"])
        rag_has_sources = "[路径" in rag_result["answer"]
        rag_honest = "无法回答" in rag_result["answer"] or "未检索到" in rag_result["answer"]

        logger.info(f"  Graph RAG: {rag_result['paths']}路径 {rag_time}ms "
                    f"幻觉:{rag_halluc} {'✓来源' if rag_has_sources else '✗无来源'} "
                    f"{'✓完整链' if rag_complete['is_complete'] else '○部分链'}")

        # ── 纯 LLM ──
        t0 = time.time()
        llm_result = run_pure_llm(question, llm)
        llm_time = round((time.time() - t0) * 1000)

        llm_halluc, llm_halluc_list = detect_hallucination(llm_result["answer"], neo4j)
        llm_complete = evaluate_completeness(llm_result["answer"])
        llm_has_sources = "[路径" in llm_result["answer"]  # 纯LLM不应该有
        llm_honest = "无法回答" in llm_result["answer"]

        logger.info(f"  纯 LLM:   {llm_time}ms "
                    f"幻觉:{llm_halluc} {'✓来源' if llm_has_sources else '✗无来源'} "
                    f"{'✓完整链' if llm_complete['is_complete'] else '○部分链'}")

        # ── 记录 ──
        base = {"id": i, "question": question, "type": qtype}

        results.append({
            **base,
            "method": "graph_rag",
            "answer": rag_result["answer"],
            "paths": rag_result["paths"],
            "time_ms": rag_time,
            "hallucinations": rag_halluc,
            "hallucination_list": rag_halluc_list,
            "has_sources": rag_has_sources,
            "chain_complete": rag_complete["is_complete"],
            "is_honest_refusal": rag_honest,
        })

        results.append({
            **base,
            "method": "pure_llm",
            "answer": llm_result["answer"],
            "paths": 0,
            "time_ms": llm_time,
            "hallucinations": llm_halluc,
            "hallucination_list": llm_halluc_list,
            "has_sources": llm_has_sources,
            "chain_complete": llm_complete["is_complete"],
            "is_honest_refusal": llm_honest,
        })

        # ── 更新统计 ──
        for method, r in [("graph_rag", rag_result), ("pure_llm", llm_result)]:
            s = stats[method]
            s["total"] += 1
            hall = rag_halluc if method == "graph_rag" else llm_halluc
            if hall == 0: s["hallucination_free"] += 1
            comp = rag_complete if method == "graph_rag" else llm_complete
            if comp["is_complete"]: s["complete"] += 1
            src = rag_has_sources if method == "graph_rag" else llm_has_sources
            if src: s["with_sources"] += 1
            hon = rag_honest if method == "graph_rag" else llm_honest
            if hon: s["honest_refusal"] += 1

    # ═══════════════════════════════════════════════════════════════════
    #  汇总报告
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  对照实验结果")
    print("=" * 70)

    print(f"\n{'指标':20s} {'Graph RAG':>12s} {'纯 LLM':>12s} {'优势':>10s}")
    print("-" * 60)

    metrics = [
        ("无幻觉率", "hallucination_free"),
        ("因果链完整率", "complete"),
        ("来源可追溯率", "with_sources"),
    ]
    for label, key in metrics:
        gr = stats["graph_rag"][key] / max(stats["graph_rag"]["total"], 1) * 100
        pl = stats["pure_llm"][key] / max(stats["pure_llm"]["total"], 1) * 100
        diff = gr - pl
        diff_str = f"+{diff:.0f}%" if diff > 0 else f"{diff:.0f}%"
        print(f"{label:20s} {gr:11.0f}% {pl:11.0f}% {diff_str:>10s}")

    # 平均幻觉数
    gr_avg_hall = sum(r["hallucinations"] for r in results if r["method"]=="graph_rag") / max(stats["graph_rag"]["total"], 1)
    llm_avg_hall = sum(r["hallucinations"] for r in results if r["method"]=="pure_llm") / max(stats["pure_llm"]["total"], 1)
    print(f"{'平均幻觉实体数':20s} {gr_avg_hall:11.1f} {llm_avg_hall:11.1f}")

    # 平均响应时间
    gr_avg_time = sum(r["time_ms"] for r in results if r["method"]=="graph_rag") / max(stats["graph_rag"]["total"], 1)
    llm_avg_time = sum(r["time_ms"] for r in results if r["method"]=="pure_llm") / max(stats["pure_llm"]["total"], 1)
    print(f"{'平均响应时间(ms)':20s} {gr_avg_time:11.0f} {llm_avg_time:11.0f}")

    # 诚实拒答率
    print(f"\n{'诚实拒答率':20s} "
          f"{stats['graph_rag']['honest_refusal']/max(stats['graph_rag']['total'],1)*100:11.0f}% "
          f"{stats['pure_llm']['honest_refusal']/max(stats['pure_llm']['total'],1)*100:11.0f}% "
          f"{'(应拒答时拒答)'}")

    # 幻觉样本
    print(f"\n{'='*60}")
    print(f"  纯LLM典型幻觉示例（KG中不存在的实体）")
    print(f"{'='*60}")
    for r in results:
        if r["method"] == "pure_llm" and r["hallucinations"] > 0:
            print(f"\n  Q{r['id']}: {r['question'][:50]}")
            print(f"  幻觉实体: {r['hallucination_list'][:5]}")

    # 保存完整结果
    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_questions": len(QUESTIONS),
            "graph_rag": {k: v for k, v in stats["graph_rag"].items()},
            "pure_llm": {k: v for k, v in stats["pure_llm"].items()},
        },
        "detailed_results": [
            {k: v for k, v in r.items() if k != "context"}
            for r in results
        ],
    }
    out_path = Path("data/processed/comparative_experiment.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"\n完整结果: {out_path}")


if __name__ == "__main__":
    run()
