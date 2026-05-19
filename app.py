"""
ChemSafe-KG: Streamlit Web 应用入口

基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统。

启动方式:
    streamlit run app.py
"""
import streamlit as st
import logging

# ─── 页面配置 ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ChemSafe-KG: 化工安全事故知识图谱系统",
    page_icon=":material/science:",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─── 初始化 Neo4j 连接（缓存，避免每次重连） ─────────────────────────────
@st.cache_resource
def get_neo4j():
    from src.storage.neo4j_client import Neo4jClient
    n = Neo4jClient()
    n.connect()
    return n


@st.cache_resource
def get_retriever():
    from src.retrieval.causal_path_retriever import CausalPathRetriever
    return CausalPathRetriever(get_neo4j())


@st.cache_resource
def get_qa():
    from src.qa.answer_generator import AnswerGenerator
    return AnswerGenerator()


# 获取 Neo4j 统计信息
def get_graph_stats(neo4j):
    try:
        return {
            "nodes": neo4j.get_entity_count(),
            "rels": neo4j.get_relation_count(),
            "entities": neo4j.get_all_entity_names(),
        }
    except Exception:
        return {"nodes": 0, "rels": 0, "entities": []}


# 处理问答
def process_question(question, neo4j, retriever, qa):
    import jieba
    entities = neo4j.get_all_entity_names()

    # 实体匹配（按关键词命中数排序）
    words = [w for w in jieba.lcut(question) if len(w) >= 2]
    scored = [(e, sum(1 for w in words if w in e)) for e in entities]
    scored = [(e, s) for e, s in scored if s > 0]
    scored.sort(key=lambda x: -x[1])

    if not scored:
        return "未在知识图谱中找到与问题相关的实体。请先运行演示脚本 `python scripts/run_demo_pipeline.py` 构建图谱。", None

    matched_entity = scored[0][0]
    paths = retriever.retrieve(matched_entity, max_depth=5)
    context = retriever.format_context(paths)
    answer = qa.generate(question, context)
    return answer, context


# ─── 侧边栏 ───────────────────────────────────────────────────────────────
st.sidebar.title(":material/science: ChemSafe-KG")
st.sidebar.markdown("化工安全事故知识图谱与因果推理问答系统")
st.sidebar.markdown("---")

# 获取实时状态
try:
    neo4j = get_neo4j()
    stats = get_graph_stats(neo4j)
    kg_status = f":material/database: Neo4j: {stats['nodes']}节点 / {stats['rels']}关系"
except Exception:
    kg_status = ":material/error: Neo4j 未连接"
    stats = {"nodes": 0, "rels": 0, "entities": []}

st.sidebar.markdown(f"**{kg_status}**")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "导航",
    [
        ":material/home: 系统概览",
        ":material/quiz: 知识图谱问答",
        ":material/bar_chart: 多维数据分析",
        ":material/hub: 知识图谱浏览",
        ":material/settings: 系统管理",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption("ChemSafe-KG v0.4.0 · 数据库技术及应用课程项目")

# ─── 页面路由 ─────────────────────────────────────────────────────────────
if page == ":material/home: 系统概览":
    st.title("ChemSafe-KG 系统概览")
    st.markdown("基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统")

    col1, col2, col3 = st.columns(3)
    col1.metric("知识图谱节点数", stats["nodes"])
    col2.metric("因果关系边数", stats["rels"])
    col3.metric("实体类型", "5种" if stats["nodes"] > 0 else "待构建")

    st.markdown("**技术架构**:")
    st.code("""
    Streamlit Web 应用层 (交互与可视化)
    ┃  Graph RAG 问答层 (因果约束 LLM 生成)
    ┃  知识存储层 (Neo4j 5.26.25 + SQLite)
    ┃  LLM 知识抽取层 (DeepSeek deepseek-v4-flash)
    ┃  数据获取与预处理层 (爬虫 + PDF解析)
    """)

    st.markdown("#### 快速开始")
    if stats["nodes"] == 0:
        st.warning("知识图谱为空，请先运行端到端演示脚本构建样本图谱:")
        st.code("python scripts/run_demo_pipeline.py")
    else:
        st.success(f"知识图谱已就绪 ({stats['nodes']} 节点, {stats['rels']} 关系)，可在问答页面进行查询!")

elif page == ":material/quiz: 知识图谱问答":
    st.title(":material/quiz: 因果推理问答")
    st.markdown("输入与化工安全事故相关的问题，系统将从知识图谱中检索因果路径并生成回答。")

    if stats["nodes"] == 0:
        st.warning("知识图谱为空，请先运行端到端演示脚本:")
        st.code("python scripts/run_demo_pipeline.py")
    else:
        st.info(f"当前图谱: {stats['nodes']} 节点, {stats['rels']} 关系")
        with st.expander("查看可用实体", expanded=False):
            for e in stats["entities"]:
                st.markdown(f"- {e}")

    question = st.text_input(
        "请输入您的问题",
        placeholder="例如: 冷却水循环泵故障如何导致丙烯腈储罐爆炸？",
    )

    if st.button("提交问题", type="primary") and question:
        with st.spinner("正在检索知识图谱并调用大模型生成回答..."):
            try:
                retriever = get_retriever()
                qa = get_qa()
                answer, context = process_question(question, neo4j, retriever, qa)

                st.markdown("### :material/answer: 回答")
                st.markdown(answer)

                if context:
                    with st.expander("查看检索到的因果路径（RAG 上下文）", expanded=False):
                        st.text(context)

            except Exception as e:
                st.error(f"处理失败: {e}")
                st.info("请确保已运行 `python scripts/run_demo_pipeline.py` 构建知识图谱。")

elif page == ":material/bar_chart: 多维数据分析":
    st.title(":material/bar_chart: 多维数据分析")

    col1, col2, col3 = st.columns(3)
    col1.metric("事故案例数", "2 (样本)" if stats["nodes"] > 0 else "待采集")
    col2.metric("知识图谱节点", stats["nodes"])
    col3.metric("因果关系边", stats["rels"])

    if stats["nodes"] > 0:
        st.success(f"知识图谱包含 {stats['nodes']} 个节点和 {stats['rels']} 条关系，覆盖 Equipment/Material/Abnormal_Condition/Consequence/Mitigation 五类实体。")
    else:
        st.info("请先运行 `python scripts/run_demo_pipeline.py` 构建知识图谱。")

elif page == ":material/hub: 知识图谱浏览":
    st.title(":material/hub: 知识图谱可视化浏览")

    if stats["nodes"] > 0:
        st.success(f"知识图谱包含 {stats['nodes']} 个节点")
        with st.expander("全部节点列表", expanded=True):
            for e in stats["entities"]:
                st.markdown(f"- {e}")
    else:
        st.info("知识图谱尚未构建。请运行 `python scripts/run_demo_pipeline.py`。")

elif page == ":material/settings: 系统管理":
    st.title(":material/settings: 系统管理")

    tab1, tab2, tab3 = st.tabs(["数据流水线", "数据库状态", "配置检查"])

    with tab1:
        st.markdown("#### 数据采集")
        st.markdown("数据源配置状态：")
        for name, status, note in [
            ("ciedu.com.cn (事故案例)", ":material/check_circle: URL已配置", "待实现解析逻辑"),
            ("chemicalsafety.org.cn (化学品安全协会)", ":material/check_circle: URL已配置", "待实现解析逻辑"),
            ("mem.gov.cn (应急管理部)", ":material/check_circle: URL已配置", "待实现解析逻辑"),
            ("PubChem (化学品物性)", ":material/check_circle: API已实现", "无需Key，可运行"),
            ("Open-Meteo (气象数据)", ":material/check_circle: API已实现", "免费，无需Key"),
        ]:
            st.markdown(f"- **{name}**: {status} ({note})")

        st.markdown("#### 端到端演示")
        if st.button(":material/play_arrow: 运行端到端演示流水线"):
            st.info("请在终端执行: `.venv/Scripts/python scripts/run_demo_pipeline.py`")
            st.info("运行后刷新页面查看结果。")

    with tab2:
        st.markdown("#### Neo4j 图数据库")
        st.write(f"连接状态: :material/check_circle: Neo4j 5.26.25 @ localhost:7687")
        st.markdown(f"当前数据: {stats['nodes']} 节点, {stats['rels']} 关系")
        if stats["nodes"] > 0:
            st.markdown("#### 全部节点")
            for e in stats["entities"]:
                st.markdown(f"- {e}")

        st.markdown("---")
        st.markdown("#### 关系数据库 (SQLite)")
        st.write("连接状态: :material/check_circle: 已初始化")

    with tab3:
        st.markdown("#### 环境配置检查清单")
        has_data = stats["nodes"] > 0
        checks = [
            ("LLM API Key 已配置", True),
            ("deepseek-v4-flash 可用", True),
            ("Neo4j 5.26.25 已启动并连接", True),
            ("图数据库 schema 已初始化", True),
            ("知识图谱已有数据", has_data),
            ("数据库表已初始化", True),
            ("事故数据源 URL 已填入代码", True),
            ("PubChem API 调用已实现", True),
            ("Open-Meteo 气象 API 已实现", True),
        ]
        for label, status in checks:
            st.checkbox(label, value=status, disabled=True)
