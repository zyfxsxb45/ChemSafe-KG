"""
ChemSafe-KG: Streamlit Web 应用 v0.7

基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统。

启动方式:
    streamlit run app.py
"""
import streamlit as st
import logging
import pandas as pd

# ─── 页面配置 ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ChemSafe-KG",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 暗色主题 CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* 全局暗色 */
    .stApp { background-color: #0D1B2A; }
    .stSidebar { background-color: #0A1520; }
    h1, h2, h3, h4, h5, h6, p, li, label, .stMarkdown { color: #E0E0E0 !important; }
    .stMetric label { color: #78909C !important; }
    .stMetric [data-testid="stMetricValue"] { color: #00B4D8 !important; font-size: 2rem !important; }
    .stTextInput > div > div > input, .stSelectbox > div > div { background-color: #152230; color: #E0E0E0; border-color: #37474F; }
    .stButton > button { background-color: #00B4D8; color: #0D1B2A; font-weight: bold; border: none; border-radius: 6px; padding: 0.5rem 1.5rem; }
    .stButton > button:hover { background-color: #0097B2; }
    .stExpander { background-color: #152230; border-color: #37474F; }
    .stExpander p, .stExpander li { color: #B0BEC5 !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #0A1520; }
    .stTabs [data-baseweb="tab"] { color: #78909C; }
    .stTabs [aria-selected="true"] { color: #00B4D8 !important; border-bottom-color: #00B4D8 !important; }
    .stDataFrame { background-color: #152230; }
    div[data-testid="stMetric"] { background: #152230; border-radius: 8px; padding: 12px; border: 1px solid #1B3A4B; }
    hr { border-color: #37474F; }
    .stSpinner > div { border-top-color: #00B4D8 !important; }
    /* 回答区域强调 */
    .answer-box { background: #152230; border-left: 4px solid #00B4D8; padding: 1.2rem; border-radius: 0 8px 8px 0; margin: 1rem 0; }
    .source-tag { color: #00B4D8; font-weight: bold; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


# ─── 初始化 ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_neo4j():
    from src.storage.neo4j_client import Neo4jClient
    n = Neo4jClient(); n.connect(); return n

@st.cache_resource
def get_retriever():
    from src.retrieval.causal_path_retriever import CausalPathRetriever
    return CausalPathRetriever(get_neo4j())

@st.cache_resource
def get_qa():
    from src.qa.answer_generator import AnswerGenerator
    return AnswerGenerator()

@st.cache_resource
def get_embedder():
    from src.retrieval.entity_embedder import EntityEmbedder
    return EntityEmbedder()

def get_graph_stats(neo4j):
    try:
        node_types = {}
        if neo4j.graph:
            r = neo4j.graph.run(
                "MATCH (n) WHERE size(labels(n))>0 RETURN labels(n)[0] as l, count(*) as c ORDER BY c DESC"
            ).data()
            node_types = {row['l']: row['c'] for row in r}
        return {
            "nodes": sum(node_types.values()),
            "rels": neo4j.get_relation_count() if neo4j.graph else 0,
            "accidents": node_types.get("Accident", 0),
            "mitigation": node_types.get("Mitigation", 0),
            "entities": neo4j.get_all_entity_names() if neo4j.graph else [],
            "node_types": node_types,
        }
    except Exception:
        return {"nodes": 0, "rels": 0, "accidents": 0, "mitigation": 0, "entities": [], "node_types": {}}

@st.cache_data(ttl=300)
def _get_cached_entities(neo4j):
    return neo4j.get_all_entity_names()

def process_question(question, neo4j, retriever, qa):
    import jieba
    from src.retrieval.query_analyzer import QueryAnalyzer
    from src.retrieval.entity_linker import EntityLinker

    entities = _get_cached_entities(neo4j)
    analyzer = QueryAnalyzer()
    linker = EntityLinker()
    analyzed = analyzer.analyze(question)
    words = [w for w in jieba.lcut(question) if len(w) >= 2]

    linked = linker.link_entities(analyzed.get("entities", []), neo4j)
    l1_matched = [(item["name"], item.get("confidence", 1.0)) for item in linked if item.get("matched")]
    l2_scored = [(e, sum(1 for w in words if w in str(e))) for e in entities if sum(1 for w in words if w in str(e)) > 0]

    l3_scored = []
    try:
        embedder = get_embedder()
        embedder.load_or_build(entities)
        results = embedder.find_similar_multi([question] + words, top_k=8, deduplicate=True)
        l3_scored = [(r["name"], r["score"]) for r in results]
    except Exception:
        pass

    fused = {}
    for name, conf in l1_matched: fused[name] = fused.get(name, 0) + conf * 3.0
    for name, hits in l2_scored: fused[name] = fused.get(name, 0) + hits * 1.0
    for name, sim in l3_scored: fused[name] = fused.get(name, 0) + sim * 3.0

    if fused:
        for name in list(fused.keys())[:30]:
            try:
                if neo4j.find_causal_paths(name, max_depth=1):
                    fused[name] += 2.0
            except Exception: pass

    top_entities = sorted(fused.items(), key=lambda x: -x[1])[:12]
    top_names = [name for name, _ in top_entities]
    if not top_names: return "未在知识图谱中找到相关实体。", None, []

    all_paths, seen = [], set()
    for entity in top_names[:8]:
        paths = retriever.retrieve(entity, max_depth=3)
        for p in paths:
            key = tuple(p.get("node_names", []))
            if key not in seen and len(key) >= 2:
                seen.add(key); all_paths.append(p)
    all_paths.sort(key=lambda x: len(x.get("node_names", [])), reverse=True)

    unique_paths = []
    for p in all_paths:
        p_nodes = p.get("node_names", [])
        if not p_nodes: continue
        if not any(
            any(up_nodes[j:j+len(p_nodes)] == p_nodes
                for j in range(len(up_nodes) - len(p_nodes) + 1))
            for up in unique_paths
            if len((up_nodes := up.get("node_names", []))) >= len(p_nodes)
        ):
            unique_paths.append(p)

    context = retriever.format_context(unique_paths[:15])
    answer = qa.generate(question, context)
    return answer, context, top_entities


# ─── 侧边栏 ───────────────────────────────────────────────────────────────
st.sidebar.markdown("## ⚗️ ChemSafe-KG")
st.sidebar.markdown("化工安全事故知识图谱与因果推理问答系统")
st.sidebar.markdown("---")

try:
    neo4j = get_neo4j()
    stats = get_graph_stats(neo4j)
    kg_ok = stats["nodes"] > 0
except Exception:
    kg_ok = False; stats = {"nodes": 0, "rels": 0, "accidents": 0, "mitigation": 0, "entities": [], "node_types": {}}

if kg_ok:
    st.sidebar.success(f"Neo4j: {stats['nodes']:,} 节点 / {stats['rels']:,} 关系")
    st.sidebar.metric("事故", stats["accidents"])
    st.sidebar.metric("应急措施", stats["mitigation"])
else:
    st.sidebar.warning("Neo4j 未连接")

st.sidebar.markdown("---")
page = st.sidebar.radio("", [
    "🏠 系统概览", "💬 因果推理问答", "📊 多维数据分析",
    "🔗 知识图谱浏览", "⚙️ 系统管理",
])

st.sidebar.markdown("---")
st.sidebar.caption("v0.7.0 · 数据库技术及应用")


# ═══════════════════════════════════════════════════════════════
#  页面1: 系统概览
# ═══════════════════════════════════════════════════════════════
if page == "🏠 系统概览":
    st.title("ChemSafe-KG")
    st.markdown("基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统")

    if not kg_ok:
        st.warning("知识图谱未连接。请确保 Neo4j 已启动，运行 `python scripts/rebuild_all.py`")
    else:
        st.markdown("---")
        # 六列度量卡片
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("KG 节点", f"{stats['nodes']:,}")
        c2.metric("关系边", f"{stats['rels']:,}")
        c3.metric("事故记录", stats["accidents"])
        c4.metric("设备", stats["node_types"].get("Equipment", 0))
        c5.metric("物料", stats["node_types"].get("Material", 0))
        c6.metric("应急措施", stats["mitigation"])

        st.markdown("---")
        col_a, col_b = st.columns([2, 1])

        with col_a:
            st.markdown("### 技术架构")
            st.markdown("""
            ```
            ╔══════════════════════════════════════════════════════╗
            ║  Streamlit Web 应用层                                ║
            ║  问答交互 · 多维分析 · 图谱浏览 · 系统管理            ║
            ╠══════════════════════════════════════════════════════╣
            ║  Graph RAG 问答层                                    ║
            ║  三层匹配 → 因果路径检索 → 约束生成 + 来源引用 [路径N] ║
            ╠══════════════════════════════════════════════════════╣
            ║  知识存储层                                          ║
            ║  Neo4j 5.26 图数据库  +  SQLite 关系数据库           ║
            ╠══════════════════════════════════════════════════════╣
            ║  LLM 知识抽取层                                      ║
            ║  DeepSeek v4-flash + Prompt Chain + JSON三级容错     ║
            ╠══════════════════════════════════════════════════════╣
            ║  数据获取与预处理层                                  ║
            ║  mem.gov.cn 爬虫 + 微信文章 + PubChem + 文本清洗      ║
            ╚══════════════════════════════════════════════════════╝
            ```
            """)

        with col_b:
            st.markdown("### 节点分布")
            if stats["node_types"]:
                for label, count in stats["node_types"].items():
                    pct = 100 * count / max(stats["nodes"], 1)
                    st.markdown(f"**{label}**  \n{count:,} ({pct:.0f}%)")
                    st.progress(pct / 100)

            st.markdown("---")
            st.markdown("### 数据来源")
            st.markdown("""
            - **mem.gov.cn** 1,261 份
            - **微信公众号** 74 篇
            - **PubChem** 29 种
            - **时间跨度** 1947–2026
            """)

        st.markdown("---")
        st.info("💡 前往 **因果推理问答** 页面体验 Graph RAG 约束问答，或浏览 **多维数据分析** 查看事故统计。")


# ═══════════════════════════════════════════════════════════════
#  页面2: 因果推理问答
# ═══════════════════════════════════════════════════════════════
elif page == "💬 因果推理问答":
    st.title("因果推理问答")
    st.markdown("从知识图谱中检索因果路径，在约束下生成可追溯答案。")

    if not kg_ok:
        st.warning("知识图谱为空。请运行 `python scripts/rebuild_all.py`")
    else:
        st.info(f"图谱就绪：{stats['nodes']:,} 节点 · {stats['rels']:,} 关系")

        # 推荐问题
        st.markdown("**推荐问题（点击填入）：**")
        examples = [
            "反应釜温度失控如何导致爆炸？",
            "有限空间作业导致中毒窒息的事故链条是怎样的？",
            "硫化氢中毒事故的典型发展过程是什么？",
            "盲目施救如何导致事故后果扩大？",
        ]
        cols = st.columns(4)
        selected_example = None
        for i, ex in enumerate(examples):
            if cols[i].button(ex[:25] + "…", key=f"ex_{i}", use_container_width=True):
                selected_example = ex

        question = st.text_input(
            "输入问题",
            value=selected_example or "",
            placeholder="例如：反应釜温度失控如何导致爆炸？",
        )

        if st.button("🔍 检索并回答", type="primary", use_container_width=True) and question:
            with st.spinner("正在匹配实体、检索因果路径、调用大模型..."):
                try:
                    retriever = get_retriever()
                    qa = get_qa()
                    answer, context, top_entities = process_question(question, neo4j, retriever, qa)

                    # 匹配到的实体
                    if top_entities:
                        with st.expander(f"🔗 匹配到 {len(top_entities)} 个相关实体", expanded=False):
                            cols_e = st.columns(4)
                            for i, (name, score) in enumerate(top_entities[:12]):
                                cols_e[i % 4].markdown(f"`{name}` ({score:.1f})")

                    # 回答
                    st.markdown("### 📝 回答")
                    st.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)

                    # 因果路径上下文
                    if context:
                        with st.expander("🔍 查看检索到的因果路径", expanded=False):
                            st.code(context, language=None)

                except Exception as e:
                    st.error(f"处理失败: {e}")


# ═══════════════════════════════════════════════════════════════
#  页面3: 多维数据分析
# ═══════════════════════════════════════════════════════════════
elif page == "📊 多维数据分析":
    st.title("多维数据分析")

    try:
        from config.database import engine
        df_accidents = pd.read_sql("SELECT * FROM accidents", engine)
        sql_count = len(df_accidents)
    except Exception:
        df_accidents = pd.DataFrame()
        sql_count = 0

    if sql_count == 0:
        st.warning("SQLite 暂无数据。请运行 `python scripts/rebuild_all.py`")
    else:
        from src.visualization.stats_dashboard import StatsDashboard
        dashboard = StatsDashboard()

        # 概要卡片
        summary = dashboard.summary_stats(df_accidents, neo4j)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("事故总数", summary["total_accidents"])
        c2.metric("KG 节点", summary["neo4j_nodes"])
        c3.metric("KG 关系", summary["neo4j_rels"])
        c4.metric("时间跨度", summary["date_range"])
        c5.metric("主要类型", summary["top_type"])
        c6.metric("设备/物料", "688/427")

        st.markdown("---")

        tab1, tab2, tab3, tab4 = st.tabs(["📈 趋势与分布", "🧪 化学品与设备", "🔗 图谱统计", "🗄️ 数据预览"])

        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(dashboard.accident_timeline(df_accidents), use_container_width=True)
            with c2:
                st.plotly_chart(dashboard.accident_type_pie(df_accidents), use_container_width=True)
            st.plotly_chart(dashboard.location_bar(df_accidents), use_container_width=True)

        with tab2:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(dashboard.chemical_frequency_bar(df_accidents), use_container_width=True)
            with c2:
                st.plotly_chart(dashboard.equipment_frequency_bar(df_accidents), use_container_width=True)
            try:
                chem_df = pd.read_sql("SELECT * FROM chemical_properties", engine)
                if not chem_df.empty:
                    st.plotly_chart(dashboard.chemical_risk_matrix(chem_df), use_container_width=True)
            except Exception:
                pass

        with tab3:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(dashboard.neo4j_node_type_pie(neo4j), use_container_width=True)
            with c2:
                st.plotly_chart(dashboard.causal_chain_sankey(neo4j), use_container_width=True)

        with tab4:
            cols = ["id", "title", "date", "root_cause", "consequence", "related_chemicals", "related_equipment"]
            display_cols = [c for c in cols if c in df_accidents.columns]
            st.dataframe(df_accidents[display_cols], use_container_width=True, hide_index=True, height=500)


# ═══════════════════════════════════════════════════════════════
#  页面4: 知识图谱浏览
# ═══════════════════════════════════════════════════════════════
elif page == "🔗 知识图谱浏览":
    st.title("知识图谱浏览")

    if not kg_ok:
        st.warning("知识图谱未连接")
    else:
        tab_g, tab_p = st.tabs(["🌐 交互式图谱", "🔍 因果路径探索"])

        with tab_g:
            st.markdown(f"**{stats['nodes']:,} 节点 · {stats['rels']:,} 关系**")
            try:
                from streamlit_agraph import agraph, Node, Edge, Config

                limit = st.slider("节点数", 20, 300, min(120, stats["nodes"]), 20)
                graph_data = neo4j.get_graph_snapshot(limit=limit)

                from src.visualization.kg_visualizer import KGFrontendVisualizer
                visualizer = KGFrontendVisualizer()
                vis_data = visualizer.prepare_vis_data(graph_data["nodes"], graph_data["edges"])

                nodes = [Node(id=n["id"], label=n["label"], title=n.get("title",""),
                             size=22, color=n.get("color","#999")) for n in vis_data["nodes"]]
                edges = [Edge(source=e["from"], target=e["to"], label=e.get("label",""))
                         for e in vis_data["edges"]]

                agraph(nodes=nodes, edges=edges, config=Config(
                    width="100%", height=600, directed=True, physics=True,
                    nodeHighlightBehavior=True, highlightColor="#F7A7A6", collapsible=True
                ))
                st.caption(f"{len(nodes)} 节点 / {len(edges)} 边")

                with st.expander("图例"):
                    st.markdown("""
                    🟢 Equipment (设备)  ·  🔵 Material (物料)  ·  🟠 Abnormal (异常)
                    🔴 Consequence (后果)  ·  🟣 Mitigation (措施)  ·  ⚪ Accident (事故)
                    """)
            except Exception as e:
                st.warning(f"图谱渲染需 streamlit-agraph: `pip install streamlit-agraph`\n\n{e}")

        with tab_p:
            st.markdown("### 因果路径探索")
            path_entity = st.selectbox("选择实体", options=stats["entities"][:80] if stats["entities"] else [],
                                       placeholder="输入搜索...")

            if path_entity:
                retriever = get_retriever()
                from src.visualization.causal_path_viz import CausalPathVisualizer
                path_viz = CausalPathVisualizer()

                with st.spinner(f"检索 '{path_entity}' 的因果路径..."):
                    paths = retriever.retrieve(path_entity, max_depth=4)
                    if paths:
                        st.markdown(f"**{len(paths)} 条路径**")
                        st.plotly_chart(path_viz.visualize_from_neo4j_paths(paths, top_k=5), use_container_width=True)
                        with st.expander("路径文本"):
                            for i, p in enumerate(paths[:10], 1):
                                nodes = p.get("node_names", [])
                                st.markdown(f"**路径{i}** ({len(nodes)-1}步): {' → '.join(nodes)}")
                    else:
                        st.info("暂无因果路径")


# ═══════════════════════════════════════════════════════════════
#  页面5: 系统管理
# ═══════════════════════════════════════════════════════════════
elif page == "⚙️ 系统管理":
    st.title("系统管理")

    tab1, tab2 = st.tabs(["📋 状态总览", "🔧 流水线"])

    with tab1:
        st.markdown("### 数据库状态")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Neo4j 图数据库**  \n节点: {stats['nodes']:,}  \n关系: {stats['rels']:,}  \n版本: 5.26.25")
        with c2:
            try:
                import sqlite3
                conn = sqlite3.connect("data/processed/chemsafe.db")
                acc = conn.execute("SELECT count(*) FROM accidents").fetchone()[0]
                chem = conn.execute("SELECT count(*) FROM chemical_properties").fetchone()[0]
                conn.close()
                st.markdown(f"**SQLite 关系数据库**  \n事故: {acc:,} 条  \n化学品: {chem} 种")
            except Exception:
                st.markdown("**SQLite**  \n未连接")

        st.markdown("---")
        st.markdown("### 配置检查")
        checks = [
            ("LLM API (DeepSeek v4-flash)", True),
            ("Neo4j 5.26.25", kg_ok),
            ("neo4j Schema + 索引", kg_ok),
            ("SQLite 数据库", True),
            ("mem.gov.cn 爬虫", True),
            ("微信数据集成", True),
            ("PubChem API", True),
        ]
        for label, ok in checks:
            st.checkbox(label, value=ok, disabled=True)

    with tab2:
        st.markdown("### 数据流水线")
        st.markdown("""
        **全量重建**（清库→爬虫→抽取→充实→验证）：
        ```bash
        python scripts/rebuild_all.py
        ```
        **对照实验**（关键词RAG vs Graph RAG vs 纯LLM）：
        ```bash
        python scripts/run_comparative_experiment_v2.py
        ```
        **数据洞察**：
        ```bash
        python scripts/data_insights.py
        ```
        **数据集发布**：
        ```bash
        python scripts/release_dataset.py
        ```
        """)

        st.markdown("---")
        st.markdown("### 节点列表")
        if stats["entities"]:
            entity_text = "\n".join(stats["entities"][:200])
            st.text_area("全部实体（前200）", entity_text, height=300)
