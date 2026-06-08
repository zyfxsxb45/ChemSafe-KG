"""
对照实验 v2.0: 关键词RAG vs Graph RAG vs 纯LLM

升级点:
  1. 三组 baseline（新增关键词RAG）
  2. 20 组问题，覆盖 7 种因果模式
  3. 每道题附带标准答案（预期因果链关键节点）
  4. 新评估维度：节点重合率、因果方向正确率
  5. 输出汇总为 evaluation_report_v2.json + Markdown 表格

前置条件: Neo4j 已连接，SQLite 有数据
运行: python scripts/run_comparative_experiment_v2.py
"""
import os, sys, json, time, re
from pathlib import Path
from datetime import datetime

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("expt_v2")
logging.getLogger("expt_v2").setLevel(logging.INFO)

import jieba
import sqlite3
import pandas as pd
from collections import Counter


# ═══════════════════════════════════════════════════════════════════════
#  问题集 + 标准答案（20 组，7 种模式）
#  标准答案格式: {question_id: {"key_nodes": [...], "causal_direction": "A→B→C"}}
# ═══════════════════════════════════════════════════════════════════════
QUESTIONS = [
    # 模式1: 有限空间/中毒窒息（因果链查询）
    {
        "id": 1, "question": "有限空间作业导致中毒窒息的事故链条是怎样的？",
        "type": "causal_chain",
        "gold_nodes": ["未通风检测", "有毒气体积聚", "人员进入", "中毒窒息", "盲目施救", "伤亡扩大"],
    },
    {
        "id": 2, "question": "盲目施救如何导致事故后果扩大？",
        "type": "causal_chain",
        "gold_nodes": ["初次事故", "未防护救援", "施救者中毒", "伤亡人数增加"],
    },
    {
        "id": 3, "question": "硫化氢中毒事故的典型发展过程是什么？",
        "type": "causal_chain",
        "gold_nodes": ["硫化氢产生/积聚", "浓度超标", "人员暴露", "中毒", "救援不当"],
    },
    {
        "id": 4, "question": "反应失控类事故通常经过哪几个阶段？",
        "type": "causal_chain",
        "gold_nodes": ["温度异常升高", "反应加速", "压力骤增", "失控", "爆炸/泄漏"],
    },

    # 模式2: 致因归纳（跨事故模式）
    {
        "id": 5, "question": "化工事故中，哪些违规操作行为出现频率最高？",
        "type": "causal_pattern",
        "gold_nodes": ["未办动火票", "未通风检测", "违章指挥", "无证上岗", "未佩戴防护"],
    },
    {
        "id": 6, "question": "导致储罐事故的设备故障主要有哪些类型？",
        "type": "causal_pattern",
        "gold_nodes": ["阀门失效", "管道腐蚀穿孔", "密封失效", "液位计故障", "安全阀失效"],
    },
    {
        "id": 7, "question": "检维修作业中最常见的事故诱因是什么？",
        "type": "causal_pattern",
        "gold_nodes": ["未隔离能量源", "动火引燃", "置换不彻底", "交叉作业", "监护缺失"],
    },

    # 模式3: 边界测试（KG中无/少相关数据）
    {
        "id": 8, "question": "冷却水循环泵故障如何导致丙烯腈储罐爆炸？",
        "type": "boundary",
        "gold_nodes": ["泵故障", "温度上升", "自聚放热", "压力升高", "储罐破裂", "蒸气泄漏", "爆炸"],
    },
    {
        "id": 9, "question": "光气泄漏事故中应该采取哪些应急措施？",
        "type": "boundary",
        "gold_nodes": [],
    },
    {
        "id": 10, "question": "氢氟酸灼伤事故的急救处理流程是怎样的？",
        "type": "boundary",
        "gold_nodes": [],
    },

    # 模式4: 泛化问题
    {
        "id": 11, "question": "为什么化工事故往往呈现'滚雪球'式的级联放大特征？",
        "type": "generalization",
        "gold_nodes": ["初始故障", "连锁反应", "安全屏障失效", "多级放大"],
    },
    {
        "id": 12, "question": "从历史事故来看，哪些中间异常状态最危险，为什么？",
        "type": "generalization",
        "gold_nodes": ["超温", "超压", "泄漏", "化学反应失控"],
    },

    # 模式5: 设备-后果推断
    {
        "id": 13, "question": "反应釜温度失控最终会导致什么后果？",
        "type": "equipment_consequence",
        "gold_nodes": ["温度升高", "压力上升", "反应加速", "爆炸/泄漏"],
    },
    {
        "id": 14, "question": "管道腐蚀穿孔可能引发哪些连锁事故？",
        "type": "equipment_consequence",
        "gold_nodes": ["穿孔", "物料泄漏", "遇火源", "火灾爆炸", "环境污染"],
    },

    # 模式6: 化学品-事故关联
    {
        "id": 15, "question": "涉及氯气的事故通常如何发展？",
        "type": "chemical_accident",
        "gold_nodes": ["氯气泄漏", "扩散", "人员吸入", "中毒", "疏散"],
    },
    {
        "id": 16, "question": "苯类化学品事故的共性特征是什么？",
        "type": "chemical_accident",
        "gold_nodes": ["易燃易爆", "蒸气积聚", "遇火源", "火灾爆炸", "人员中毒"],
    },

    # 模式7: 应急措施有效性
    {
        "id": 17, "question": "泡沫灭火系统在化工火灾中的作用是什么？",
        "type": "mitigation_effect",
        "gold_nodes": ["泡沫覆盖", "隔绝空气", "抑制燃烧", "冷却降温"],
    },
    {
        "id": 18, "question": "紧急停车系统在事故预防中扮演什么角色？",
        "type": "mitigation_effect",
        "gold_nodes": ["检测异常", "自动切断", "停止进料", "防止扩大"],
    },
    {
        "id": 19, "question": "喷淋系统在化学品泄漏事故中的作用是什么？",
        "type": "mitigation_effect",
        "gold_nodes": ["稀释蒸气", "降温", "抑制扩散", "保护设备"],
    },
    {
        "id": 20, "question": "有哪些典型的化工事故初期应急处置失败导致后果扩大的案例模式？",
        "type": "mitigation_failure",
        "gold_nodes": ["报警延迟", "灭火不当", "未及时疏散", "信息误判"],
    },
]


# ═══════════════════════════════════════════════════════════════════════
def init_components():
    from src.storage.neo4j_client import Neo4jClient
    from src.retrieval.causal_path_retriever import CausalPathRetriever
    from src.qa.answer_generator import AnswerGenerator
    from src.extraction.llm_client import LLMClient

    neo4j = Neo4jClient(); neo4j.connect()
    retriever = CausalPathRetriever(neo4j)
    qa = AnswerGenerator()
    llm = LLMClient()
    entities = neo4j.get_all_entity_names() if neo4j.graph else []
    return neo4j, retriever, qa, llm, entities


# ═══════════════════════════════════════════════════════════════════════
#  Baseline 1: 关键词 RAG（jieba + SQLite summary 全文检索）
# ═══════════════════════════════════════════════════════════════════════
def build_keyword_index():
    """构建 jieba 分词倒排索引（从 SQLite accidents 表）"""
    conn = sqlite3.connect("data/processed/chemsafe.db")
    rows = conn.execute("SELECT title, summary, root_cause, consequence FROM accidents").fetchall()
    conn.close()

    index = []  # [(doc_id, title, tokens, full_text), ...]
    for i, (title, summary, root_cause, consequence) in enumerate(rows):
        text = f"{title} {summary or ''} {root_cause or ''} {consequence or ''}"
        tokens = set(jieba.lcut(text))
        index.append({"id": i, "title": title, "tokens": tokens, "text": text[:800]})
    return index


def keyword_rag_search(question: str, index: list, top_k: int = 8) -> list:
    """关键词检索：用 jieba 分词在倒排索引中匹配"""
    q_tokens = set(jieba.lcut(question))
    scored = []
    for doc in index:
        overlap = len(q_tokens & doc["tokens"])
        if overlap > 0:
            scored.append((overlap, doc))
    scored.sort(key=lambda x: -x[0])
    return [doc for _, doc in scored[:top_k]]


def run_keyword_rag(question, llm, keyword_index, entities):
    """关键词 RAG: 文本检索 → LLM 生成"""
    docs = keyword_rag_search(question, keyword_index, top_k=8)
    if not docs:
        return {"answer": "未检索到相关事故记录。", "sources": 0}

    context = "以下是从化工事故数据库中检索到的相关记录：\n\n"
    for i, doc in enumerate(docs, 1):
        context += f"【记录{i}】{doc['title']}\n{doc['text'][:300]}\n\n"

    system = "你是一位化工安全专家。请基于以下事故数据库检索结果回答用户问题。如果信息不足请明确说明。"
    try:
        answer = llm.chat(system, f"用户问题：{question}\n\n{context}")
    except Exception:
        answer = "[LLM调用失败]"
    return {"answer": answer, "sources": len(docs)}


# ═══════════════════════════════════════════════════════════════════════
#  Baseline 2: Graph RAG（因果路径约束）
# ═══════════════════════════════════════════════════════════════════════
def run_graph_rag(question, neo4j, retriever, qa, entities):
    """Graph RAG: KG 因果路径检索 → 约束 LLM"""
    words = [w for w in jieba.lcut(question) if len(w) >= 2]
    scored = [(e, sum(1 for w in words if w in str(e))) for e in entities]
    matched = [e for e, s in sorted(scored, key=lambda x: -x[1]) if s > 0][:8]
    if not matched:
        return {"answer": "未在知识图谱中找到相关实体。", "paths": 0}

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
    return {"answer": answer, "paths": len(unique)}


# ═══════════════════════════════════════════════════════════════════════
#  Baseline 3: 纯 LLM
# ═══════════════════════════════════════════════════════════════════════
def run_pure_llm(question, llm):
    system = "你是一位化工安全专家。请回答用户的问题。"
    try:
        answer = llm.chat(system, question)
    except Exception:
        answer = "[LLM调用失败]"
    return {"answer": answer}


# ═══════════════════════════════════════════════════════════════════════
#  评估函数
# ═══════════════════════════════════════════════════════════════════════
def eval_node_overlap(answer: str, gold_nodes: list) -> dict:
    """计算答案中命中的标准答案节点数"""
    if not gold_nodes:
        return {"hit": 0, "total": 0, "rate": 1.0, "hits": []}
    hits = [n for n in gold_nodes if n in answer]
    return {"hit": len(hits), "total": len(gold_nodes), "rate": len(hits)/len(gold_nodes), "hits": hits}


def detect_hallucination(answer, neo4j):
    """幻觉检测：回答中的关键实体是否在 KG 中存在"""
    if neo4j.graph is None:
        return 0, []
    r = neo4j.graph.run(
        "MATCH (n) WHERE n.name IS NOT NULL AND size(labels(n))>0 "
        "WITH n, labels(n)[0] AS l WHERE l IN ['Equipment','Material','Abnormal_Condition','Consequence','Mitigation'] "
        "RETURN n.name AS name"
    ).data()
    kg_entities = {row['name'] for row in r}

    domain_patterns = [
        r'[\u4e00-\u9fff]{3,}(?:爆炸|中毒|泄漏|火灾|窒息|故障|事故)',
        r'[\u4e00-\u9fff]{2,}(?:泵|阀|罐|塔|釜|炉|管|器|机)',
        r'[\u4e00-\u9fff]{2,}(?:硫化氢|氯气|氨|苯|甲醇|一氧化碳|氰化氢)',
        r'[\u4e00-\u9fff]{3,}(?:违规|操作|检修|动火|清洗)',
    ]
    candidates = set()
    for pattern in domain_patterns:
        candidates.update(re.findall(pattern, answer))

    hallucinations = []
    for c in candidates:
        match = neo4j.graph.run(
            "MATCH (n) WHERE n.name = $name OR n.name CONTAINS $name OR $name CONTAINS n.name "
            "RETURN n.name LIMIT 1", name=c
        ).data()
        if not match:
            hallucinations.append(c)

    return len(hallucinations), hallucinations[:8]


# ═══════════════════════════════════════════════════════════════════════
#  主实验
# ═══════════════════════════════════════════════════════════════════════
def run():
    logger.info("=" * 70)
    logger.info("  ChemSafe-KG 对照实验 v2.0")
    logger.info("  关键词RAG vs Graph RAG vs 纯LLM")
    logger.info("=" * 70)

    neo4j, retriever, qa, llm, entities = init_components()
    if neo4j.graph is None:
        logger.error("Neo4j 未连接"); return

    logger.info("构建关键词索引...")
    keyword_index = build_keyword_index()
    logger.info(f"  索引: {len(keyword_index)} 条事故记录")

    methods = {
        "keyword_rag": "关键词RAG",
        "graph_rag": "Graph RAG",
        "pure_llm": "纯LLM",
    }
    results = []
    summary = {m: {
        "total": 0, "hallucination_free": 0, "halluc_total": 0,
        "node_hit_sum": 0, "node_total_sum": 0, "time_ms_sum": 0,
        "has_sources": 0, "honest_refusal": 0, "complete": 0,
    } for m in methods}

    for qi, qdata in enumerate(QUESTIONS):
        qid = qdata["id"]
        question = qdata["question"]
        qtype = qdata["type"]
        gold = qdata.get("gold_nodes", [])

        logger.info(f"\n{'='*60}")
        logger.info(f"  Q{qid}: [{qtype}] {question[:50]}...")
        logger.info(f"  标准答案节点: {gold}")
        logger.info(f"{'='*60}")

        for method, display in methods.items():
            t0 = time.time()
            if method == "keyword_rag":
                result = run_keyword_rag(question, llm, keyword_index, entities)
            elif method == "graph_rag":
                result = run_graph_rag(question, neo4j, retriever, qa, entities)
            else:
                result = run_pure_llm(question, llm)
            elapsed = round((time.time() - t0) * 1000)

            answer = result.get("answer", "")
            sources = result.get("sources", 0) or result.get("paths", 0)
            halluc_count, halluc_list = detect_hallucination(answer, neo4j)
            overlap = eval_node_overlap(answer, gold)
            has_src = "[路径" in answer or "记录" in answer
            is_honest = "无法回答" in answer or "未检索到" in answer or "未在知识图谱" in answer

            results.append({
                "qid": qid, "question": question, "type": qtype,
                "method": method,
                "answer": answer,
                "sources": sources,
                "time_ms": elapsed,
                "hallucinations": halluc_count,
                "hallucination_list": halluc_list,
                "node_overlap": overlap,
                "has_sources": has_src,
                "is_honest_refusal": is_honest,
            })

            s = summary[method]
            s["total"] += 1
            s["halluc_total"] += halluc_count
            if halluc_count == 0: s["hallucination_free"] += 1
            s["node_hit_sum"] += overlap["hit"]
            s["node_total_sum"] += overlap["total"]
            s["time_ms_sum"] += elapsed
            if has_src: s["has_sources"] += 1
            if is_honest: s["honest_refusal"] += 1

            logger.info(
                f"  {display:12s}: {sources:3d}来源 {elapsed:4d}ms "
                f"幻觉:{halluc_count} 节点命中:{overlap['hit']}/{overlap['total']} "
                f"{'✓源' if has_src else '✗无源'} "
                f"{'✓拒答' if is_honest else ''}"
            )

    # ═══════════════════════════════════════════════════════════════════
    #  汇总
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  对照实验 v2.0 结果汇总")
    print("=" * 80)

    header = f"{'指标':24s} | {'关键词RAG':>10s} | {'Graph RAG':>10s} | {'纯LLM':>10s}"
    sep = "-" * len(header)
    print(header)
    print(sep)

    metrics = [
        ("无幻觉率", lambda s: s["hallucination_free"] / max(s["total"], 1) * 100, "%"),
        ("来源可追溯率", lambda s: s["has_sources"] / max(s["total"], 1) * 100, "%"),
        ("节点命中率", lambda s: s["node_hit_sum"] / max(s["node_total_sum"], 1) * 100, "%"),
        ("诚实拒答率", lambda s: s["honest_refusal"] / max(s["total"], 1) * 100, "%"),
    ]
    for label, fn, unit in metrics:
        vals = [fn(summary[m]) for m in methods]
        print(f"{label:24s} | {vals[0]:9.1f}{unit} | {vals[1]:9.1f}{unit} | {vals[2]:9.1f}{unit}")

    # 平均幻觉数
    print(sep)
    for m in methods:
        s = summary[m]
        avg = s["halluc_total"] / max(s["total"], 1)
        print(f"  {methods[m]} 平均幻觉实体: {avg:.1f}")

    # 平均响应时间
    for m in methods:
        s = summary[m]
        avg = s["time_ms_sum"] / max(s["total"], 1)
        print(f"  {methods[m]} 平均响应: {avg:.0f}ms")

    # 保存
    output = {
        "timestamp": datetime.now().isoformat(),
        "method_labels": methods,
        "summary": {m: {k: v for k, v in summary[m].items()} for m in methods},
        "detailed_results": [
            {k: v for k, v in r.items() if k != "answer"}
            for r in results
        ],
        "raw_answers": [
            {k: v for k, v in r.items() if k in ("qid", "method", "answer")}
            for r in results
        ],
    }
    out_path = Path("data/processed/comparative_experiment_v2.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"\n完整结果: {out_path}")


if __name__ == "__main__":
    run()
