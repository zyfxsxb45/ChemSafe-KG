# ChemSafe-KG

> **基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统**  
> 数据库技术及应用课程项目 · 大二下  
> **v0.7.0** — 6,976 节点 / 23,111 关系 · 1,579 事故 · 三组对照实验 · 9×幻觉减少

---

## 项目简介

ChemSafe-KG 是一个端到端的化工安全知识图谱系统，核心创新点：

1. **LLM 驱动的自动化 KG 构建** — Prompt Chain 策略驱动 DeepSeek 从 1,300+ 份非结构化事故报告中自动抽取实体与因果链，8 条迭代规则 + Few-shot 示例 + JSON 3 级容错，成功率 99%+
2. **因果约束的 Graph RAG 问答** — 三层实体匹配（精确/关键词/嵌入语义）→ Cypher 因果路径检索 → 约束生成 + 来源引用。三组对照实验（关键词RAG / Graph RAG / 纯LLM）证明：幻觉减少 **9 倍**，诚实拒答率从 0% 提升至 55%
3. **多源数据融合分析** — mem.gov.cn 全量月度汇编（1,261 份）+ 微信公众号事故分析（74 篇）+ PubChem 化学品物性（72 种）+ 历史天气（108 条），双存储（Neo4j + SQLite）+ 跨源链接

覆盖课程全部核心模块：Pandas 数据处理、SQL/图数据库、LLM4Data、Data4LLM、数据可视化。

## 数据规模（v0.7 全量重建）

| 指标 | 数值 |
|------|------|
| 知识图谱节点 | **6,976**（Abnormal 3,570 / Accident 1,579 / Equipment 688 / Consequence 641 / Material 427 / Mitigation 71） |
| 因果关系边 | **23,111** |
| SQLite 事故记录 | **1,579**（100% 含根原因与后果，79% 含日期） |
| 事故报告来源 | **1,261** 份 mem.gov.cn + **74** 篇微信公众号（拆分为 326 段独立事故） |
| 化学品物性 | **72** 种（含闪点26种、爆炸极限31种、毒性分类43种） |
| 天气记录 | **108** 条（Open-Meteo历史天气，匹配事故地点日期） |
| 事故时间跨度 | 1947–2026（79 年） |

## 核心实验结果（三组对照实验，20 题 × 7 种因果模式）

| 指标 | 关键词RAG | Graph RAG | 纯 LLM |
|------|----------|-----------|--------|
| 无幻觉率 | 40% | **70%** | 5% |
| 来源可追溯率 | 100% | 55% | 0% |
| 诚实拒答率 | 10% | **55%** | 0% |
| 平均幻觉实体数 | 1.2 | **0.65** | 5.95 |

> Graph RAG 比纯 LLM 减少 **9 倍**幻觉。详见 `scripts/run_comparative_experiment_v2.py`

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env   # 填入 LLM_API_KEY 和 Neo4j 密码

# 3. 全量重建（推荐，一键完成所有步骤）
python scripts/rebuild_all.py

# 4. 或分阶段运行
python pipeline.py --stage acquisition  # 爬虫采集
python pipeline.py --stage extraction   # LLM 抽取
python pipeline.py --stage enrich       # 数据充实
python pipeline.py --stage qa           # 问答验证

# 5. 续抽取（只处理新增文件）
python scripts/continue_extraction.py

# 6. 对照实验（三组 baseline）
python scripts/run_comparative_experiment_v2.py

# 7. 启动 Web 应用
streamlit run app.py                    # → http://localhost:8501
```

## 系统架构

```
Streamlit Web 应用层 (问答 + 可视化 + 管理)
┃  Graph RAG 问答层 (三层实体融合 → 因果路径检索 → 约束生成 + 来源引用)
┃  知识存储层 (Neo4j 5.26.25 + SQLite + 4索引 + 分析视图 + 跨源链接)
┃  LLM 知识抽取层 (DeepSeek deepseek-v4-flash + Prompt Chain + JSON 3级容错)
┃  数据获取与预处理层 (爬虫 + 文本清洗 + 多源融合)
```

## 项目结构

```
ChemSafe-KG/
├── app.py                          # Streamlit 应用入口（5页面）
├── pipeline.py                     # CLI 全流程编排器
├── config/                         # 全局配置
├── src/
│   ├── acquisition/                # 爬虫（mem.gov.cn/CSB）+ PubChem + Open-Meteo
│   ├── preprocessing/              # 文本清洗 + PDF解析 + 多源融合
│   ├── extraction/                 # LLM 抽取引擎（Prompt Chain + JSON容错 + 事件原子化）
│   ├── storage/                    # Neo4j + SQLite + Schema + 跨源链接 + Accident聚合
│   ├── retrieval/                  # 因果路径检索 + 三层实体匹配 + 嵌入语义
│   ├── qa/                         # Graph RAG 约束问答 + 降级处理
│   └── visualization/              # 10种图表 + 因果路径有向图 + KG可视化
├── scripts/
│   ├── rebuild_all.py               # ★ 全量重建（清库→爬虫→微信→抽取→充实→验证）
│   ├── continue_extraction.py       # 续抽取（只处理新增文件，断点续跑）
│   ├── process_wechat_data.py       # 微信公众号数据预处理
│   ├── run_demo_pipeline.py         # 端到端演示
│   ├── run_extraction_pipeline.py   # 批量抽取
│   ├── run_evaluation.py            # 综合评估（SQL×8 + QA×6 + E/R图 + 性能基准）
│   ├── run_comparative_experiment_v2.py # 三组对照实验（关键词RAG/GraphRAG/纯LLM × 20题）
│   ├── data_insights.py             # 数据洞察分析（6维度 → Markdown报告）
│   ├── release_dataset.py           # 数据集发布（CSV + DATASET_CARD）
│   ├── verify_rebuild.py            # 重建后健康检查
│   ├── backfill_dates.py            # 日期回填
│   ├── normalize_source_url.py      # source_url 格式统一
│   ├── enrich_data.py               # 数据充实
│   ├── init_db.py                   # 初始化
│   └── seed_data.py                 # 种子数据
├── data/                           # 原始/处理后/外部数据
└── docs/
    └── framework-guide.md           # 详细框架说明
```

## 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| 图数据库 | Neo4j 5.26.25 + py2neo | 知识图谱存储与因果路径查询 |
| 关系数据库 | SQLite + SQLAlchemy（4索引 + 1分析视图） | 结构化数据存储 |
| LLM 服务 | DeepSeek deepseek-v4-flash（OpenAI 协议） | 实体抽取、答案生成 |
| 前端 | Streamlit + Plotly + streamlit-agraph | 交互式 Web 应用 |
| 嵌入匹配 | sentence-transformers（v0.6: 实体清洗 + 自适应阈值 + 三层融合） | 语义实体对齐 |
| 分词 | jieba | 中文分词与实体提取 |
| 数据采集 | requests + BeautifulSoup + lxml | 爬虫（mem.gov.cn） |
| 化学品 API | pubchempy（PubChem，免费） | 物性数据查询 |
| 气象 API | Open-Meteo（免费，1940年起） | 历史天气数据查询 |

## Web 应用功能

| 页面 | 功能 |
|------|------|
| **系统概览** | 实时 Neo4j 节点/关系统计，架构图 |
| **因果推理问答** | 自然语言输入 → 三层实体融合 → 因果路径检索 → Graph RAG 约束生成 → 答案 + [路径N]来源引用 |
| **多维数据分析** | 4 标签页：趋势分布、化学品设备频次、图谱统计（饼图+桑基图）、数据表预览 |
| **知识图谱浏览** | streamlit-agraph 交互式图谱 + 实体搜索因果路径探索 + 路径有向图可视化 |
| **系统管理** | 数据流水线控制、数据库状态、配置检查清单 |

## 数据采集

| 数据源 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| **mem.gov.cn** 应急管理部 | P1 | ✅ 1,261 份 | 全量月度汇编页，含根因分析 |
| **微信公众号** 事故分析 | P1 | ✅ 74 篇 | 含防范措施与教训反思，Mitigation 主要来源 |
| **PubChem** 化学品物性 | P0 | ✅ 29 种 | 100% 含分子量/CAS/IUPAC |
| **Open-Meteo** 气象数据 | P2 | ✅ 8 条 | 34 省坐标覆盖 |
| CSB 美国化学品安全委员会 | P2 | ✅ requests 降级 | JS 渲染需 browser tool |
| ciedu.com.cn 事故案例库 | P0 | ⚠️ CAPTCHA | 需 browser tool 接入 |

## 对比实验

| 指标 | Graph RAG | 纯 LLM |
|------|-----------|--------|
| 来源可追溯 | **90%** | 0% |
| 因果链完整 | **90%** | 60% |
| 平均幻觉数 | **4.4** | 13.2 |
| 诚实拒答 | ✅ | ❌ |

```bash
python scripts/run_comparative_experiment.py
# 输出: data/processed/comparative_experiment.json
```

## 综合评估

```bash
python scripts/run_evaluation.py
# 输出: SQL×8 + QA×6 + E/R图 + Neo4j性能基准
```

## 开发进度

| 周次 | 任务 | 状态 |
|------|------|------|
| 9–16 | 全周期 | ✅ **全部完成** |

## 详细文档

详见 [框架说明文档](docs/framework-guide.md)，包含五层架构详解、TODO 清单、技术债务与风险说明。

## 项目成员

- 翟彝凡（化工系）
- 余亮阳（化工系）
- 赵乐毅（化工系）

指导老师：王健楠 教授

本项目仅用于课程学习目的。
