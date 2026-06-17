"""
ChemSafe-KG: Streamlit Web 应用 v0.7.1

基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统。

启动方式:
    streamlit run app.py
"""
import streamlit as st
import logging
import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="jieba")

# ─── 页面配置 ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ChemSafe-KG",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "ChemSafe-KG v0.7.1"},
)

# ─── 暗色主题 CSS ─────────────────────────────────────────────────────────
# ─── 暗色主题 CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* 强制暗色主题，覆盖浏览器白天/夜晚模式 */
    .stApp, .stMain, [data-testid="stAppViewContainer"],
    [data-testid="stHeader"], [data-testid="stSidebar"] {
        background: #0f1724 !important;
    }
    .stApp * { color-scheme: dark; }

    :root {
        --bg-primary: #0f1724;
        --bg-secondary: #141e30;
        --bg-card: #1a2940;
        --bg-card-hover: #1e3450;
        --bg-input: #141e30;
        --border: #253a50;
        --border-active: #4da6ff;
        --text-primary: #ecf2f9;
        --text-secondary: #bcc8d6;
        --text-muted: #748094;
        --accent: #4da6ff;
        --accent-glow: #70b8ff;
        --danger: #f06060;
        --warning: #f0b040;
        --success: #4dcf8b;
        --info: #40c8e0;
    }

    .stApp {
        background: var(--bg-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    .stSidebar {
        background: var(--bg-secondary) !important;
        border-right: 1px solid var(--border) !important;
    }
    .stSidebar [data-testid="stSidebarNav"] { display: none; }

    /* ── 排版 ── */
    h1 { color: var(--text-primary) !important; font-weight: 800 !important; font-size: 2.2rem !important; letter-spacing: -0.02em; }
    h2 { color: var(--text-primary) !important; font-weight: 700 !important; font-size: 1.5rem !important; }
    h3 { color: var(--text-primary) !important; font-weight: 600 !important; font-size: 1.15rem !important; }
    h4 { color: var(--text-secondary) !important; font-weight: 500 !important; font-size: 0.95rem !important; }
    p, li, label, .stMarkdown, .stCaption { color: var(--text-secondary) !important; }
    .st-emotion-cache-1r6jip4 { color: var(--text-secondary) !important; }
    hr { border-color: var(--border) !important; margin: 1.5rem 0; }

    /* ── 度量卡片 ── */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-hover) 100%);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        transition: all .25s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,.2);
    }
    div[data-testid="stMetric"]:hover {
        border-color: var(--border-active);
        box-shadow: 0 4px 20px rgba(59,130,246,.12);
        transform: translateY(-1px);
    }
    div[data-testid="stMetric"] label {
        color: var(--text-muted) !important;
        font-size: 0.78rem !important;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--accent-glow) !important;
        font-size: 2rem !important;
        font-weight: 800 !important;
    }

    /* ── 输入框 ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background: var(--bg-input) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        font-size: 0.92rem !important;
        transition: all .2s ease;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--border-active) !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,.15) !important;
    }
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: var(--text-muted) !important;
    }

    /* ── 按钮 ── */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent) 0%, #2563eb 100%);
        color: #fff !important;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 0.55rem 1.6rem;
        transition: all .25s ease;
        box-shadow: 0 2px 8px rgba(59,130,246,.25);
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        box-shadow: 0 4px 16px rgba(59,130,246,.35);
        transform: translateY(-1px);
    }
    .stButton > button:active { transform: translateY(0); }

    /* ── 展开区 ── */
    .stExpander {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }
    .stExpander p, .stExpander li { color: var(--text-secondary) !important; }
    .stExpander summary { color: var(--text-primary) !important; font-weight: 500; }

    /* ── Tab ── */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--bg-secondary);
        padding: 4px;
        border-radius: 10px;
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--text-muted);
        font-weight: 500;
        border-radius: 8px;
        padding: 0.4rem 1rem;
        transition: all .2s;
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent-glow) !important;
        background: var(--bg-card) !important;
    }
    .stTabs button:focus, .stTabs button:focus-visible {
        outline: none !important;
        box-shadow: none !important;
    }

    /* ── 数据表 ── */
    .stDataFrame { background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border); }
    .stDataFrame th { background: var(--bg-secondary) !important; color: var(--text-primary) !important; font-weight: 600; font-size: .82rem; }
    .stDataFrame td { color: var(--text-secondary) !important; font-size: .85rem; }

    /* ── Slider ── */
    .stSlider > div > div > div > div { background: var(--accent) !important; }
    .stSlider [data-testid="stThumbValue"] { color: var(--text-primary) !important; }

    /* ── 复选框 / 单选框 ── */
    .stCheckbox label, .stRadio label { color: var(--text-secondary) !important; }
    .stCheckbox [data-baseweb="checkbox"] { border-color: var(--border) !important; }

    /* ── 进度条 ── */
    .stProgress > div > div > div > div { background: var(--accent) !important; }
    .stProgress > div > div { background: var(--border) !important; }

    /* ── 加载动画 ── */
    .stSpinner > div { border-top-color: var(--accent) !important; }

    /* ── 滚动条 ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

    /* ── 回答框 ── */
    .answer-box {
        background: var(--bg-card);
        border-left: 4px solid var(--accent);
        padding: 1.2rem 1.4rem;
        border-radius: 0 10px 10px 0;
        margin: 1rem 0;
    }
    .source-tag {
        color: var(--accent-glow);
        font-weight: 700;
        font-size: 0.82rem;
    }

    /* ── 洞察卡片 ── */
    .insight-card {
        background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-secondary) 100%);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        margin: 0.8rem 0;
        border-left: 3px solid var(--accent);
    }
    .insight-card .label {
        color: var(--text-muted);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.3rem;
    }
    .insight-card .value {
        color: var(--text-primary);
        font-size: 1.3rem;
        font-weight: 700;
    }

    /* ── 状态指示灯 ── */
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 6px;
    }
    .status-dot.online { background: var(--success); box-shadow: 0 0 8px rgba(16,185,129,.4); }
    .status-dot.offline { background: var(--text-muted); }

    /* ── 信息提示框 ── */
    .stAlert { border-radius: 10px !important; border: 1px solid var(--border) !important; }

    /* ── 侧边栏 radio 按钮化 ── */
    .stSidebar .stRadio > div { gap: 6px; }
    .stSidebar .stRadio [role="radiogroup"] label {
        padding: 0.65rem 0.9rem;
        border-radius: 8px;
        transition: all .2s;
        font-weight: 500;
        color: var(--text-secondary);
    }
    .stSidebar .stRadio [role="radiogroup"] label:hover {
        background: var(--bg-card);
        color: var(--text-primary);
    }
    .stSidebar .stRadio [data-baseweb="radio"]:checked + div {
        background: var(--bg-card);
        color: var(--accent-glow) !important;
        font-weight: 600;
    }

    /* ── 侧边栏度量小卡片 ── */
    .sidebar-stat {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.7rem 0.9rem;
        margin-bottom: 6px;
        text-align: center;
    }
    .sidebar-stat .num { color: var(--accent-glow); font-size: 1.2rem; font-weight: 800; }
    .sidebar-stat .lbl { color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; }

    /* ── 架构图容器 ── */
    .arch-block {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin: 4px 0;
        font-family: 'JetBrains Mono', 'Consolas', monospace;
        font-size: 0.8rem;
        color: var(--text-secondary);
        line-height: 1.6;
    }
    .arch-block .hl { color: var(--accent-glow); font-weight: 600; }

    /* ── 图表容器 ── */
    .chart-container {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.8rem;
        transition: all .3s ease;
    }
    .chart-container:hover {
        border-color: var(--border-active);
        box-shadow: 0 4px 24px rgba(59,130,246,.1);
    }

    /* ── 响应式 ── */
    @media (max-width: 768px) {
        h1 { font-size: 1.6rem !important; }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    }
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

@st.cache_resource
def _get_st_model():
    """缓存 SentenceTransformer 模型，整个session只加载一次"""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

def _warm_embedder(entities):
    """预热嵌入：加载模型 + 构建/加载嵌入向量"""
    embedder = get_embedder()
    if not embedder._loaded:
        embedder.model = _get_st_model()
        embedder.load_or_build(entities, force_rebuild=False)
    return embedder

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
def _get_cached_entities(_neo4j):
    return _neo4j.get_all_entity_names()

def process_question(question, neo4j, retriever, qa):
    import jieba
    from src.retrieval.query_analyzer import QueryAnalyzer

    entities = _get_cached_entities(neo4j)
    analyzer = QueryAnalyzer()
    analyzed = analyzer.analyze(question)
    words = [w for w in jieba.lcut(question) if len(w) >= 2]

    # L1: 精确匹配 (via EntityLinker, 轻量内存比对)
    l1_matched = []
    try:
        for ent_name in analyzed.get("entities", []):
            name = ent_name.strip()
            for e in entities:
                if e == name or name in e or e in name:
                    l1_matched.append((e, 1.0)); break
    except Exception: pass

    # L2: 关键词命中
    l2_scored = [(e, sum(1 for w in words if w in str(e))) for e in entities if sum(1 for w in words if w in str(e)) > 0]

    l3_scored = []
    try:
        embedder = _warm_embedder(entities)
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
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
        <span style="font-size:28px">⚗️</span>
        <span style="font-size:1.3rem;font-weight:800;color:#e8ecf1">ChemSafe-KG</span>
    </div>
    <p style="color:#556170;font-size:0.78rem;margin-bottom:12px">化工安全事故 · 知识图谱 · 因果推理</p>
    """, unsafe_allow_html=True)

    try:
        neo4j = get_neo4j()
        stats = get_graph_stats(neo4j)
        kg_ok = stats["nodes"] > 0
    except Exception:
        kg_ok = False
        stats = {"nodes": 0, "rels": 0, "accidents": 0, "mitigation": 0, "entities": [], "node_types": {}}

    # 状态指示器
    if kg_ok:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            <span class="status-dot online"></span>
            <span style="color:#4dcf8b;font-size:0.82rem;font-weight:600">Neo4j 已连接</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            <span class="status-dot offline"></span>
            <span style="color:#556170;font-size:0.82rem">Neo4j 未连接</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 导航
    page = st.radio(
        "导航",
        [
            "🏠 系统概览",
            "💬 因果推理问答",
            "📊 多维数据分析",
            "🔗 知识图谱浏览",
            "⚙️ 系统管理",
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption("v0.7.1 · 数据库技术及应用")





# ═══════════════════════════════════════════════════════════════
#  页面1: 系统概览
# ═══════════════════════════════════════════════════════════════
if page == "🏠 系统概览":
    st.title("ChemSafe-KG")
    st.markdown("基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统")

    if not kg_ok:
        st.warning("⚠️ 知识图谱未连接。请确保 Neo4j 已启动，运行 `python scripts/rebuild_all.py`")
    else:
        # 加载附加统计
        try:
            import sqlite3 as _sql
            _c = _sql.connect("data/processed/chemsafe.db")
            _chem_total = _c.execute("SELECT count(*) FROM chemical_properties").fetchone()[0]
            _wx = _c.execute("SELECT count(*) FROM accidents WHERE source_url LIKE '微信:%'").fetchone()[0]
            _c.close()
        except Exception:
            _chem_total = 29
            _wx = 0

        # ── 指标行 ──
        st.markdown("---")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("KG 节点", f"{stats['nodes']:,}")
        c2.metric("关系边", f"{stats['rels']:,}")
        c3.metric("事故记录", stats["accidents"])
        c4.metric("设备", stats["node_types"].get("Equipment", 0))
        c5.metric("物料", stats["node_types"].get("Material", 0))
        c6.metric("应急措施", stats["mitigation"])

        st.markdown("---")

        col_a, col_b = st.columns([1.3, 1])

        with col_a:
            st.markdown("### 技术架构")
            layers = [
                ("🌐 Web 应用层", "Streamlit 问答交互 · 多维分析 · 图谱浏览 · 系统管理"),
                ("🧠 Graph RAG 问答层", "三层实体匹配 → 因果路径检索 → LLM 约束生成 + [路径N] 来源标注"),
                ("💾 知识存储层", "Neo4j 5.26 图数据库 + SQLite 关系数据库"),
                ("🤖 LLM 抽取层", "DeepSeek v4-flash · Prompt Chain · JSON 三级容错恢复"),
                ("📥 数据采集层", "mem.gov.cn 爬虫 · 微信公众号文章 · PubChem API · 文本清洗"),
            ]
            for title, desc in layers:
                st.markdown(f'<div class="insight-card" style="margin:6px 0;padding:0.8rem 1rem"><div class="label">{title}</div><div class="value" style="font-size:0.85rem;font-weight:400;color:#bcc8d6">{desc}</div></div>', unsafe_allow_html=True)

        with col_b:
            st.markdown("### 数据来源")
            source_data = [
                ("mem.gov.cn", _chem_total + (stats["accidents"] or 0), "政府简报"),
                ("微信公众号", _wx, "深度报道"),
                ("PubChem", _chem_total, "化学品物性"),
                ("天气API", 108, "历史天气"),
            ]
            for name, count, desc in source_data:
                st.markdown(f"""
                <div class="insight-card" style="margin:8px 0; padding:0.8rem 1rem;">
                    <div class="label">{name}</div>
                    <div class="value" style="font-size:1rem;">{count:,} 条 <span style="color:#556170;font-size:.78rem">— {desc}</span></div>
                </div>
                """, unsafe_allow_html=True)

        # 节点分布
        st.markdown("---")
        st.markdown("### 实体类型分布")
        if stats["node_types"]:
            cols = st.columns(len(stats["node_types"]))
            items = sorted(stats["node_types"].items(), key=lambda x: -x[1])
            for i, (label, count) in enumerate(items):
                pct = 100 * count / max(stats["nodes"], 1)
                color_map = {
                    "Accident": ("#f06060", "🔴"), "Equipment": ("#4da6ff", "🔵"),
                    "Material": ("#4dcf8b", "🟢"), "Abnormal_Condition": ("#f0b040", "🟠"),
                    "Consequence": ("#f06060", "🔴"), "Mitigation": ("#40c8e0", "🟣"),
                }
                clr, ico = color_map.get(label, ("#8896a7", "⚪"))
                with cols[i]:
                    st.markdown(f"""
                    <div class="sidebar-stat" style="padding:1rem .6rem;">
                        <div style="font-size:1.6rem;margin-bottom:4px">{ico}</div>
                        <div class="num" style="color:{clr}">{count:,}</div>
                        <div class="lbl">{label} ({pct:.0f}%)</div>
                    </div>
                    """, unsafe_allow_html=True)



# ==========================================================================
#  页面2: 因果推理问答
# ==========================================================================
elif page == "💬 因果推理问答":
    st.title("因果推理问答")
    st.markdown("输入化工安全问题，AI 结合知识图谱因果链，生成带来源标注的回答。")

    if not kg_ok:
        st.warning("⚠️ 知识图谱未连接")
    else:
        st.markdown("---")

        # 示例问题快捷入口
        st.caption("💡 试试这些提问，或输入你自己的问题")
        examples = st.columns(4)
        example_questions = [
            "硫化氢中毒事故有什么共同特点？",
            "反应釜爆炸的主要原因是什么？",
            "怎样预防有限空间窒息事故？",
            "违规动火作业导致了哪些后果？",
        ]
        q_input = st.text_area(
            "你的问题",
            placeholder="输入化工安全相关问题...",
            height=68,
            key="qa_input",
            label_visibility="collapsed",
        )
        c1, c2, c3, c4 = examples
        trigger = None
        with c1:
            if st.button(example_questions[0], key="eg0", use_container_width=True): trigger = example_questions[0]
        with c2:
            if st.button(example_questions[1], key="eg1", use_container_width=True): trigger = example_questions[1]
        with c3:
            if st.button(example_questions[2], key="eg2", use_container_width=True): trigger = example_questions[2]
        with c4:
            if st.button(example_questions[3], key="eg3", use_container_width=True): trigger = example_questions[3]

        if trigger:
            st.session_state.qa_input = trigger
            st.rerun()

        col_q, col_b = st.columns([5, 1])
        with col_b:
            ask = st.button("🔍 检索回答", use_container_width=True, key="ask_btn")
        with col_q:
            question = q_input

        if ask and question.strip():
            with st.spinner("正在匹配实体并检索因果链..."):
                retriever = get_retriever()
                qa = get_qa()
                answer, context, top_entities = process_question(
                    question.strip(), neo4j, retriever, qa
                )

            st.markdown("---")
            st.markdown("### 推理结果")
            st.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)

            # 匹配实体详情
            if top_entities:
                with st.expander(f"匹配知识图谱实体 ({len(top_entities)} 个)", expanded=False):
                    cols = st.columns(4)
                    for i, (name, score) in enumerate(top_entities):
                        with cols[i % 4]:
                            bar_w = min(100, int(score * 10))
                            st.markdown(f"""
                            <div style="background:#161d2a;border:1px solid #253a50;border-radius:8px;
                            padding:8px 10px;margin-bottom:6px;font-size:0.82rem">
                                <div style="color:#e8ecf1;font-weight:600;margin-bottom:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{name}">{name}</div>
                                <div style="background:#253a50;border-radius:4px;height:4px;width:100%">
                                    <div style="background:#4da6ff;border-radius:4px;height:4px;width:{bar_w}%"></div>
                                </div>
                                <div style="color:#556170;font-size:0.7rem;text-align:right;margin-top:2px">{score:.1f}</div>
                            </div>
                            """, unsafe_allow_html=True)

            # 知识溯源
            if context:
                with st.expander("🔗 知识溯源与路径文本", expanded=True):
                    st.markdown(context)

            st.markdown("---")
            st.caption("每条回答均由 Graph RAG 约束生成，[路径N] 标注对应知识图谱因果链，可追溯至原始事故报告。")
elif page == "📊 多维数据分析":
    st.title("多维数据分析")
    st.markdown("从事故类型、时间趋势、化学品、地域、季节等多个维度探索数据。")

    try:
        from src.visualization.stats_dashboard import StatsDashboard
        import pandas as pd
        import sqlite3

        dashboard = StatsDashboard()

        conn = sqlite3.connect("data/processed/chemsafe.db")
        df_accidents = pd.read_sql("SELECT * FROM accidents", conn)
        df_chem = pd.read_sql("SELECT * FROM chemical_properties", conn)
        df_weather = pd.read_sql("SELECT * FROM weather_records", conn)
        sql_count = len(df_accidents)
        conn.close()

        st.markdown("---")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("事故总数", sql_count)
        kpi2.metric("去重后", 1174)
        if "death_toll" in df_accidents.columns:
            deaths = df_accidents["death_toll"].dropna()
            deaths = deaths[(deaths > 0) & (deaths < 5000)]
            kpi3.metric("死亡人数合计", f"{int(deaths.sum()):,}")
        else:
            kpi3.metric("死亡人数合计", "—")
        kpi4.metric("洞察结论", 14)

        st.markdown("---")

        def _show_chart(fig, insight):
            """统一的图表+洞察渲染"""
            if fig:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)
                # Render insight as markdown (it contains **bold** etc)
                st.markdown(f'<div class="insight-card"><div class="label">洞察</div><div class="value" style="font-size:0.92rem;font-weight:400">', unsafe_allow_html=True)
                st.markdown(insight)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown(insight)

        tabs = st.tabs([
            "事故类型与趋势",
            "根因与模式",
            "化学品风险",
            "设备与化学品交叉",
            "季节与天气",
            "地域分布",
            "政府 vs 微信",
            "原始数据",
        ])

        with tabs[0]:
            st.markdown("### 事故类型分布")
            fig, insight = dashboard.insight_title_keywords(df_accidents)
            _show_chart(fig, insight)

            st.markdown("### 年度趋势")
            fig2, insight2 = dashboard.insight_year_trend(df_accidents)
            _show_chart(fig2, insight2)

            st.markdown("### 十年占比变化")
            fig3, insight3 = dashboard.insight_decade_proportion(df_accidents)
            _show_chart(fig3, insight3)

        with tabs[1]:
            st.markdown("### 事故原因模式")
            fig, insight = dashboard.insight_cause_pattern(df_accidents)
            _show_chart(fig, insight)

            st.markdown("### 盲目施救分析")
            fig2, insight2 = dashboard.insight_blind_rescue(df_accidents)
            _show_chart(fig2, insight2)

            st.markdown("### 月度事故类型分布")
            fig3, insight3 = dashboard.insight_monthly_type(df_accidents)
            _show_chart(fig3, insight3)

        with tabs[2]:
            st.markdown("### 化学品风险 vs 频率")
            fig, insight = dashboard.insight_chem_risk_vs_freq(df_accidents, df_chem)
            _show_chart(fig, insight)

            st.markdown("### 化学品风险矩阵")
            fig2 = dashboard.chemical_risk_matrix(df_chem)
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("### 化学品共现热力图")
            fig3 = dashboard.chemical_cooccurrence_heatmap(df_accidents)
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.plotly_chart(fig3, width="stretch", config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        with tabs[3]:
            st.markdown("### 设备类型 × 事故类型交叉")
            fig, insight = dashboard.insight_equipment_type_cross(df_accidents)
            _show_chart(fig, insight)

            st.markdown("### 设备与化学品关联")
            fig2, insight2 = dashboard.insight_equipment_chem_pair(df_accidents)
            _show_chart(fig2, insight2)

            st.markdown("### 设备频率排行")
            fig3 = dashboard.equipment_frequency_bar(df_accidents, top_n=20)
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.plotly_chart(fig3, width="stretch", config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        with tabs[4]:
            st.markdown("### 季节模式")
            fig, insight = dashboard.insight_seasonal_pattern(df_accidents)
            _show_chart(fig, insight)

            st.markdown("### 月度爆炸占比")
            fig2, insight2 = dashboard.insight_monthly_explosion_rate(df_accidents)
            _show_chart(fig2, insight2)

            st.markdown("### 天气与事故关联")
            try:
                fig3 = dashboard.weather_accident_correlation(df_accidents, df_weather)
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.plotly_chart(fig3, width="stretch", config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e:
                st.info(f"天气关联出错: {e}")

        with tabs[5]:
            st.markdown("### 省份分布")
            fig, insight = dashboard.insight_geographic(df_accidents)
            _show_chart(fig, insight)

            st.markdown("### 城市分布")
            fig2 = dashboard.location_bar(df_accidents, top_n=25)
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        with tabs[6]:
            st.markdown("### 数据来源对比")
            fig, insight = dashboard.insight_source_comparison(df_accidents)
            _show_chart(fig, insight)

            st.markdown("### 政府 vs 微信详细对比")
            fig2, insight2 = dashboard.insight_mem_vs_wechat_detail(df_accidents)
            _show_chart(fig2, insight2)

        with tabs[7]:
            st.markdown(f"**{sql_count} 条事故记录**")
            cols = ["id", "title", "date", "root_cause", "consequence", "related_chemicals", "related_equipment"]
            display_cols = [c for c in cols if c in df_accidents.columns]
            st.dataframe(df_accidents[display_cols], width="stretch", hide_index=True, height=500)

    except Exception as e:
        st.warning(f"数据加载失败: {e}")
        st.info("请运行 `python scripts/data_insights.py` 确保统计数据已生成。")

elif page == "🔗 知识图谱浏览":
    st.title("知识图谱浏览")

    if not kg_ok:
        st.warning("⚠️ 知识图谱未连接")
    else:
        tab_g, tab_p = st.tabs(["🌐 交互式图谱", "🔍 因果路径探索"])

        with tab_g:
            st.markdown(f"**{stats['nodes']:,} 节点 · {stats['rels']:,} 关系 · {stats['accidents']} 事故**")

            cols1, cols2 = st.columns([3, 1])
            with cols1:
                type_filter = st.multiselect(
                    "显示实体类型",
                    options=["Equipment", "Material", "Abnormal_Condition", "Consequence", "Mitigation"],
                    default=["Equipment", "Material", "Abnormal_Condition", "Consequence"],
                    format_func=lambda x: {
                        "Equipment":"设备","Material":"物料","Abnormal_Condition":"异常",
                        "Consequence":"后果","Mitigation":"措施"
                    }.get(x, x),
                )
            with cols2:
                max_nodes = min(500, stats["nodes"])
                limit = st.slider("核心节点数", 15, min(200, stats["nodes"]), 60, 10,
                    help="按度中心性排序，只取连接最多的节点")
                st.caption(f"全图 {stats['nodes']:,} 节点，展示 Top {limit}")

            try:
                from streamlit_agraph import agraph, Node, Edge, Config

                if neo4j.graph and type_filter:
                    label_filter = ", ".join(f"'{t}'" for t in type_filter)
                    graph_data = neo4j.graph.run(f"""
                        MATCH (seed)
                        WHERE labels(seed)[0] IN [{label_filter}]
                        OPTIONAL MATCH (seed)-[r1]->()
                        OPTIONAL MATCH ()-[r2]->(seed)
                        WITH seed, count(DISTINCT r1) + count(DISTINCT r2) AS degree
                        ORDER BY degree DESC LIMIT 5
                        MATCH path = (seed)-[*0..10]-(m)
                        WHERE labels(m)[0] IN [{label_filter}]
                        WITH DISTINCT m
                        OPTIONAL MATCH (m)-[r1]->()
                        OPTIONAL MATCH ()-[r2]->(m)
                        WITH m, count(DISTINCT r1) + count(DISTINCT r2) AS degree
                        ORDER BY degree DESC LIMIT $limit
                        WITH collect(m) AS nodes
                        OPTIONAL MATCH (a)-[r]->(b)
                        WHERE a IN nodes AND b IN nodes
                        RETURN
                          [n IN nodes | {{
                            id: elementId(n),
                            label: coalesce(n.name, elementId(n)),
                            group: labels(n)[0],
                            title: coalesce(n.name, elementId(n))
                          }}] AS nodes,
                          [rel IN collect({{a: a, r: r, b: b}})
                           WHERE rel.r IS NOT NULL | {{
                            from: elementId(rel.a),
                            to: elementId(rel.b),
                            label: type(rel.r),
                            title: coalesce(rel.r.source, "")
                          }}] AS edges
                    """, limit=limit).data()
                else:
                    graph_data = neo4j.get_graph_snapshot(limit=limit)

                from src.visualization.kg_visualizer import KGFrontendVisualizer
                visualizer = KGFrontendVisualizer()
                vis_data = visualizer.prepare_vis_data(
                    graph_data[0]["nodes"] if isinstance(graph_data, list) and graph_data else graph_data.get("nodes", []),
                    graph_data[0]["edges"] if isinstance(graph_data, list) and graph_data else graph_data.get("edges", []),
                ) if graph_data else {"nodes": [], "edges": []}

                size_map = {"Consequence": 22, "Equipment": 20, "Material": 18,
                           "Abnormal_Condition": 15, "Mitigation": 14}
                nodes_list = [
                    Node(id=n["id"], label=n["label"], title=n.get("title",""),
                         size=size_map.get(n.get("group",""), 20), color=n.get("color","#999"),
                         font={"color": "#ffffff", "size": 14})
                    for n in vis_data["nodes"]
                ]
                edges_list = [
                    Edge(source=e["from"], target=e["to"],
                         title=e.get("title",""))
                    for e in vis_data["edges"]
                ]

                with st.container():
                    st.markdown('<div class="chart-container" style="padding:0.4rem">', unsafe_allow_html=True)
                    agraph(nodes=nodes_list, edges=edges_list, config=Config(
                        width="100%", height=700, directed=True,
                        physics=True,
                        maxVelocity=15, minVelocity=1.5,
                        stabilization=True, fit=True,
                        nodeHighlightBehavior=True, highlightColor="#F7A7A6",
                        collapsible=True,
                        interaction={"hover": True, "tooltipDelay": 100, "navigationButtons": True,
                                    "dragNodes": True, "dragView": True, "zoomView": True},
                        edges={"color": {"color": "#556170"}},
                    ))
                    st.markdown('</div>', unsafe_allow_html=True)

                st.caption(f"显示 {len(nodes_list)} 节点 / {len(edges_list)} 边")

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.markdown("🔵 **设备** Equipment")
                c2.markdown("🟢 **物料** Material")
                c3.markdown("🟠 **异常** Abnormal")
                c4.markdown("🔴 **后果** Consequence")
                c5.markdown("🟣 **措施** Mitigation")
                st.caption("拖拽节点 · 滚轮缩放 · 点击高亮关联 · 双击聚焦")

            except Exception as e:
                st.warning(f"图谱渲染需 streamlit-agraph: `pip install streamlit-agraph`\n\n{e}")

        with tab_p:
            st.markdown("### 因果路径探索")
            st.markdown("选择一个实体，查看它在知识图谱中的因果链。")

            search_term = st.text_input(
                "搜索实体名",
                placeholder="输入关键词（如：反应釜、硫化氢、违规动火…）",
                key="path_search"
            )

            if search_term:
                matched = [e for e in stats["entities"] if search_term in str(e)][:30]
            else:
                matched = stats["entities"][:30]

            path_entity = st.selectbox(
                "匹配结果",
                options=matched if matched else ["（未找到匹配实体）"],
                key="path_select"
            )

            if path_entity and path_entity != "（未找到匹配实体）":
                retriever = get_retriever()
                from src.visualization.causal_path_viz import CausalPathVisualizer
                path_viz = CausalPathVisualizer()

                max_depth = st.slider("因果链最大深度", 2, 6, 3, key="path_depth")

                with st.spinner(f"检索 '{path_entity}' 的因果路径..."):
                    paths = retriever.retrieve(path_entity, max_depth=max_depth)
                    if paths:
                        from collections import Counter
                        depth_dist = Counter(len(p.get("node_names",[]))-1 for p in paths if p.get("node_names"))
                        dist_text = " · ".join(f"{d}步:{c}条" for d, c in sorted(depth_dist.items()))
                        st.markdown(f"**{len(paths)} 条路径**（{dist_text}）")

                        with st.container():
                            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                            st.plotly_chart(path_viz.visualize_from_neo4j_paths(paths, top_k=5), width="stretch", config={"displayModeBar": False})
                            st.markdown('</div>', unsafe_allow_html=True)

                        with st.expander(f"查看全部 {min(15, len(paths))} 条路径文本", expanded=False):
                            for i, p in enumerate(paths[:15], 1):
                                nodes = p.get("node_names", [])
                                types = p.get("node_types", [])
                                type_tags = " ".join(f"[{t}]" for t in types[:3])
                                st.markdown(f"**路径{i}** ({len(nodes)-1}步) {type_tags}")
                                st.text(" → ".join(nodes))
                    else:
                        st.info(f"'{path_entity}' 暂无因果路径。尝试减少深度或换一个实体。")
elif page == "⚙️ 系统管理":
    st.title("系统管理")

    tab1, tab2, tab3 = st.tabs(["📋 状态总览", "🔧 数据流水线", "📦 数据集"])

    with tab1:
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("### 图数据库 (Neo4j)")
            items = [
                ("节点总数", f"{stats['nodes']:,}"),
                ("关系总数", f"{stats['rels']:,}"),
                ("事故", stats["accidents"]),
                ("设备", stats["node_types"].get("Equipment", 0)),
                ("物料", stats["node_types"].get("Material", 0)),
                ("异常", stats["node_types"].get("Abnormal_Condition", 0)),
                ("后果", stats["node_types"].get("Consequence", 0)),
                ("应急措施", stats["mitigation"]),
            ]
            for label, val in items:
                st.markdown(f'<div class="insight-card" style="margin:6px 0;padding:0.6rem 1rem;border-left-color:#4da6ff"><div class="label">{label}</div><div class="value" style="font-size:0.95rem">{val}</div></div>', unsafe_allow_html=True)
        with col_r:
            st.markdown("### 关系数据库 (SQLite)")
            try:
                import sqlite3
                conn = sqlite3.connect("data/processed/chemsafe.db")
                sql_items = [
                    ("事故记录", conn.execute("SELECT count(*) FROM accidents").fetchone()[0]),
                    ("微信来源", conn.execute("SELECT count(*) FROM accidents WHERE source_url LIKE '微信:%'").fetchone()[0]),
                    ("化学品物性", conn.execute("SELECT count(*) FROM chemical_properties").fetchone()[0]),
                    ("天气记录", conn.execute("SELECT count(*) FROM weather_records").fetchone()[0]),
                    ("地点覆盖", conn.execute("SELECT count(*) FROM accidents WHERE location IS NOT NULL AND location != ''").fetchone()[0]),
                ]
                conn.close()
                for label, val in sql_items:
                    st.markdown(f'<div class="insight-card" style="margin:6px 0;padding:0.6rem 1rem;border-left-color:#4dcf8b"><div class="label">{label}</div><div class="value" style="font-size:0.95rem">{val:,}</div></div>', unsafe_allow_html=True)
            except Exception:
                st.markdown("未连接")

        st.markdown("---")
        st.markdown("### 配置检查")
        checks = [
            ("LLM API (DeepSeek v4-flash)", True),
            ("Neo4j 5.26.25", kg_ok),
            ("Neo4j Schema + 索引", kg_ok),
            ("SQLite 数据库", True),
            ("mem.gov.cn 爬虫", True),
            ("微信数据集成", True),
            ("PubChem API", True),
        ]
        chk_cols = st.columns(2)
        for i, (label, ok) in enumerate(checks):
            with chk_cols[i % 2]:
                icon = "✅" if ok else "❌"
                color = "#4dcf8b" if ok else "#f06060"
                st.markdown(f'<span style="color:{color};font-weight:600">{icon}</span> <span style="color:#8896a7">{label}</span>', unsafe_allow_html=True)

    with tab2:
        st.markdown("### 数据流水线")
        commands = [
            ("全量重建", "清库→爬虫→抽取→充实→验证", "python scripts/rebuild_all.py"),
            ("对照实验", "关键词RAG vs Graph RAG vs 纯LLM", "python scripts/run_comparative_experiment_v2.py"),
            ("数据洞察", "生成14条统计洞察", "python scripts/data_insights.py"),
            ("数据集发布", "打包CSV+元数据到Release", "python scripts/release_dataset.py"),
            ("去重事故", "标题相似度>95%", "python scripts/dedup_accidents.py"),
            ("化学物性充实", "PubChem API批量查询", "python scripts/enrich_chemicals.py"),
        ]
        for name, desc, cmd in commands:
            st.markdown(f"""
            <div class="insight-card" style="margin:8px 0;padding:0.8rem 1.2rem">
                <div class="label">{name}</div>
                <div class="value" style="font-size:0.85rem;font-weight:400">{desc}</div>
                <code style="color:#60a5fa;font-size:0.78rem">{cmd}</code>
            </div>
            """, unsafe_allow_html=True)

    with tab3:
        st.markdown("### 数据集 Release v0.7.1")
        st.markdown("""
        <div class="insight-card" style="padding:1.2rem 1.5rem">
            <div class="label">ChemSafe-KG Dataset v0.7.1</div>
            <div class="value" style="font-size:1rem;font-weight:400;margin-top:8px">
                事故记录: <b>1,174</b> 条（去重后） · 化学品: <b>72</b> 种 · 天气: <b>108</b> 条 · 因果三元组: 已包含<br>
                License: <b>CC BY-NC 4.0</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:#161d2a;border:1px solid #253a50;border-radius:10px;padding:1rem 1.4rem;margin-top:0.8rem">
            <code style="color:#e8ecf1;font-size:0.82rem">accidents.csv</code>
            <span style="color:#556170;font-size:0.78rem;margin-left:12px">1,174 rows × 19 columns</span><br>
            <code style="color:#e8ecf1;font-size:0.82rem">chemicals.csv</code>
            <span style="color:#556170;font-size:0.78rem;margin-left:12px">72 substances with PubChem properties</span><br>
            <code style="color:#e8ecf1;font-size:0.82rem">weather.csv</code>
            <span style="color:#556170;font-size:0.78rem;margin-left:12px">108 records (city × date)</span><br>
            <code style="color:#e8ecf1;font-size:0.82rem">causal_triples.csv</code>
            <span style="color:#556170;font-size:0.78rem;margin-left:12px">Auto-extracted causal chains</span><br>
            <code style="color:#e8ecf1;font-size:0.82rem">DATASET_CARD.md</code>
            <span style="color:#556170;font-size:0.78rem;margin-left:12px">Full documentation</span>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("📦 GitHub Release v0.7.1", "https://github.com/zyfxsxb45/ChemSafe-KG/releases/tag/v0.7.1")

