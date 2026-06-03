# ChemSafe-KG

> **基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统**  
> 数据库技术及应用课程项目 · 大二下  
> **v0.5.0** — 1,538 节点 / 1,727 关系 · 200 份真实事故 · 统计仪表盘 · 因果路径可视化 · 多源融合

---

## 项目简介

ChemSafe-KG 是一个端到端的化工安全知识图谱系统，核心创新点：

1. **LLM 驱动的自动化 KG 构建** — Prompt Chain 策略驱动 DeepSeek 从非结构化事故报告中自动抽取实体与因果链，174/200 成功率
2. **因果约束的 Graph RAG 问答** — 利用知识图谱中的因果路径约束 LLM 生成空间，每条陈述标注来源路径，避免幻觉与逻辑跳跃
3. **多源数据融合分析** — 事故报告 + 29 种危化品物性 + 历史气象数据，构建统一多维分析视图

覆盖课程全部核心模块：Pandas 数据处理、SQL/图数据库、LLM4Data、Data4LLM、数据可视化。

## 数据规模

| 指标 | 数值 |
|------|------|
| 知识图谱节点 | **1,538**（Abnormal_Condition 1,076 / Consequence 185 / Equipment 166 / Material 107 / Mitigation 4） |
| 因果关系边 | **1,727** |
| SQLite 事故记录 | **187**（100% 含根原因与后果摘要） |
| 化学品物性 | **29** 种（100% 含分子量、IUPAC 名、CAS 号） |
| 气象记录 | **8** 条（Open-Meteo 真实历史天气） |
| 事故时间跨度 | 1947–2026（79 年） |
| 事故类型 | 爆炸 87 · 中毒 42 · 窒息 20 · 火灾 15 · 泄漏 7 |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env   # 编辑 .env，填入 LLM_API_KEY 和 Neo4j 密码

# 3. 初始化数据库
python scripts/init_db.py

# 4. 全流程一键运行
python pipeline.py --stage all          # 采集→抽取→充实→问答验证
# 或分阶段:
python pipeline.py --stage acquisition  # 爬虫采集
python pipeline.py --stage extraction   # LLM 抽取
python pipeline.py --stage enrich       # 数据充实
python pipeline.py --stage qa           # 问答验证

# 5. 启动 Web 应用
streamlit run app.py                    # → http://localhost:8501
```

## 系统架构

```
Streamlit Web 应用层 (问答 + 可视化 + 管理)
┃  Graph RAG 问答层 (因果约束 LLM 生成，答案引用来源标注)
┃  知识存储层 (Neo4j 5.26.25 + SQLite + 4索引 + 分析视图)
┃  LLM 知识抽取层 (DeepSeek deepseek-v4-flash + Prompt Chain)
┃  数据获取与预处理层 (爬虫 + 清洗 + 多源融合)
```

## 项目结构

```
ChemSafe-KG/
├── app.py                          # Streamlit 应用入口（5页面）
├── pipeline.py                     # CLI 全流程编排器（acquisition/extraction/enrich/qa）
├── config/                         # 全局配置
│   ├── settings.py                 # 统一配置入口（LLM/DB/路径/爬虫）
│   ├── database.py                 # SQLAlchemy 引擎与 Session
│   └── llm_config.py               # LLM API 客户端工厂
├── src/
│   ├── acquisition/                # 数据获取
│   │   ├── report_crawler.py       # 事故爬虫（mem.gov.cn 95月度页 / CSB）
│   │   ├── chemical_api.py         # 化学品物性（PubChem via pubchempy）
│   │   └── weather_fetcher.py      # 气象数据（Open-Meteo，34省坐标）
│   ├── preprocessing/              # 数据预处理
│   │   ├── text_cleaner.py         # 文本清洗与标准化
│   │   ├── pdf_parser.py           # PDF 解析（pdfplumber）
│   │   └── data_merger.py          # 多源融合（事故↔化学品↔气象）
│   ├── extraction/                 # LLM 知识抽取（核心创新①）
│   │   ├── llm_client.py           # OpenAI 兼容封装（重试/JSON模式）
│   │   ├── prompt_templates.py     # Prompt Chain（5实体/3关系/Few-shot）
│   │   ├── entity_extractor.py     # 实体关系抽取引擎
│   │   └── result_validator.py     # 结构验证与置信度评分
│   ├── storage/                    # 知识存储
│   │   ├── neo4j_client.py         # Neo4j CRUD/批量写入/路径查询
│   │   ├── schema_manager.py       # 图Schema（6节点/6关系/索引约束）
│   │   └── relational_db.py        # SQLAlchemy ORM（3表）
│   ├── retrieval/                  # Graph RAG 检索
│   │   ├── causal_path_retriever.py # 因果路径查询 + 格式化（含类型标签）
│   │   ├── query_analyzer.py        # 意图检测 + jieba 实体提取
│   │   ├── entity_linker.py         # 三级实体匹配（精确→包含→反向）
│   │   ├── entity_embedder.py       # 语义嵌入匹配（sentence-transformers）
│   │   └── cypher_generator.py      # 动态 Cypher 模板生成
│   ├── qa/                         # 因果推理问答（核心创新②）
│   │   ├── answer_generator.py      # LLM 答案生成 + 降级
│   │   ├── context_builder.py       # RAG 上下文构建（含来源引用要求）
│   │   └── fallback_handler.py      # 全文检索降级 + 模板应答
│   └── visualization/              # 前端可视化
│       ├── stats_dashboard.py       # 统计仪表盘（10种图表）
│       ├── causal_path_viz.py       # 因果路径有向图（5色节点/3线型）
│       └── kg_visualizer.py         # Neo4j→vis.js 转换（类型着色+大小）
├── scripts/
│   ├── run_demo_pipeline.py         # 端到端演示（样本→Neo4j→问答）
│   ├── run_extraction_pipeline.py   # 批量知识抽取（.txt→LLM→Neo4j+SQLite）
│   ├── enrich_data.py               # 数据充实（化学品+气象+融合视图）
│   ├── fix_database.py              # 数据库修复与索引创建
│   ├── init_db.py                   # 数据库初始化
│   └── seed_data.py                 # 种子数据插入
├── data/
│   ├── raw/accident_reports/        # 爬虫输出的200份事故文本
│   ├── processed/                   # chemsafe.db + 嵌入缓存 + 融合视图
│   └── external/                    # 化学品物性CSV + 天气CSV
└── docs/
    └── framework-guide.md           # 详细框架说明（五层架构+27项TODO清单）
```

## 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| 图数据库 | Neo4j 5.26.25 + py2neo | 知识图谱存储与因果路径查询 |
| 关系数据库 | SQLite + SQLAlchemy（4索引 + 1分析视图） | 结构化数据存储 |
| LLM 服务 | DeepSeek deepseek-v4-flash（OpenAI 协议） | 实体抽取、答案生成 |
| 前端 | Streamlit + Plotly + streamlit-agraph | 交互式 Web 应用 |
| 嵌入匹配 | sentence-transformers（MiniLM-L12-v2） | 语义实体对齐 |
| 分词 | jieba | 中文分词与实体提取 |
| 数据采集 | requests + BeautifulSoup + lxml | 爬虫（mem.gov.cn） |
| 化学品 API | pubchempy（PubChem，免费） | 物性数据查询 |
| 气象 API | Open-Meteo（免费，1940年起） | 历史天气数据查询 |
| 配置 | python-dotenv | 环境变量管理 |

## Web 应用功能

| 页面 | 功能 |
|------|------|
| **系统概览** | 实时 Neo4j 节点/关系统计，架构图 |
| **因果推理问答** | 自然语言输入 → 三层实体匹配 → 因果路径检索 → Graph RAG 约束生成 → 答案+来源引用 |
| **多维数据分析** | 4 标签页：趋势分布（年份/月度/地区）、化学品设备频次、图谱统计（节点类型饼图+因果桑基图）、数据表预览 |
| **知识图谱浏览** | streamlit-agraph 交互式图谱 + 实体搜索因果路径探索 + 路径有向图可视化 |
| **系统管理** | 数据流水线控制、数据库状态、配置检查清单 |

## 数据采集

| 数据源 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| **mem.gov.cn** 历史上的危化品事故 | P1 | ✅ 200 份已采集 | 95 个月度页，每页 17–41 起事故，含根因分析 |
| **PubChem** 化学品物性 | P0 | ✅ 29 种已入库 | 100% 含分子量/IUPAC名/CAS号 |
| **Open-Meteo** 气象数据 | P0 | ✅ 8 条采样 | 全球历史天气，34 省坐标覆盖 |
| CSB 美国化学品安全委员会 | P2 | ✅ requests 降级 | JS 渲染需 browser tool 补全 |
| ciedu.com.cn 事故案例库 | P0 | ⚠️ CAPTCHA | 含完整调查报告，需 browser tool 接入 |
| ichemsafe.com | P2 | ❌ 需登录 | 待评估 |

## 运行验证

```bash
# LLM API
python -c "from config.llm_config import get_llm_client; print([m.id for m in get_llm_client().models.list()])"

# Neo4j
python -c "from py2neo import Graph; from config.settings import neo4j; g=Graph(neo4j.URI,auth=(neo4j.USER,neo4j.PASSWORD)); print(g.run('MATCH (n) RETURN count(n)').data())"

# 端到端演示
python scripts/run_demo_pipeline.py

# QA 验证
python pipeline.py --stage qa
```

## 开发进度

| 周次 | 任务 | 状态 |
|------|------|------|
| 9–10 | 环境配置 + 技术选型 | ✅ |
| 11 | 数据采集爬虫 | ✅（mem.gov.cn 200 份） |
| 12–13 | LLM 抽取 + Neo4j + Graph RAG + 前端 | ✅ |
| 14 | 数据扩充 + 多源融合 + EDA | ✅（174/200 抽取，融合视图就绪） |
| 15 | 可视化 + 性能优化 + QA 增强 | ✅（10 种图表 + 路径可视化 + 来源引用） |
| 16 | 集成测试 + 报告撰写 + 演示准备 | ⚡ 当前 |

## 详细文档

详见 [框架说明文档](docs/framework-guide.md)，包含：
- 五层架构详解（每层模块接口、当前状态、TODO 清单）
- 26 项待办按 P0/P1/P2/P3 优先级分组
- 外部数据源与资源清单（含 URL）
- 技术债务与风险说明

## 项目成员

- 翟彝凡（化工系）
- 余亮阳（化工系）
- 赵乐毅（化工系）

指导老师：王健楠 教授

本项目仅用于课程学习目的。
