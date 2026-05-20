# ChemSafe-KG

> **基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统**  
> 数据库技术及应用课程项目 · 大二下  
> **当前状态：v0.4.1 — 批量 KG 构建含 SQLite 双写入，若干条真实事故 QA 实测通过**

---

## 项目简介

ChemSafe-KG 是一个端到端的化工安全知识图谱系统，核心创新点：

1. **LLM 驱动的自动化 KG 构建** — 设计 Prompt Chain 策略，使大模型从非结构化事故报告中自动抽取实体与因果链
2. **因果约束的 Graph RAG 问答** — 利用知识图谱中的因果路径约束 LLM 生成空间，避免幻觉与逻辑跳跃

系统覆盖课程全部核心模块：Pandas数据处理、SQL/图数据库、LLM4Data、Data4LLM、数据可视化等。

## 当前状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 基础设施 | ✅ 完成 | DeepSeek API + Neo4j 5.26.25 + SQLite 全部就绪 |
| 数据采集爬虫 | ✅ 完成 | `mem.gov.cn` 历史上危化品事故栏目，94 个月度汇编页，2000+ 起事故可采集 |
| 化学品物性 API | ✅ 完成 | PubChem PUG REST（免费，无需 Key），20 种常见危化品 |
| 气象 API | ✅ 完成 | Open-Meteo（免费，无需 Key），全球历史气象数据 |
| LLM 知识抽取 | ✅ 完成 | DeepSeek deepseek-v4-flash，Prompt Chain 抽取，样本已验证 |
| 端到端演示流水线 | ✅ 验证通过 | 样本数据抽取→存储→检索→问答全链路已跑通 |
| 批量抽取流水线 | ✅ 可用 | `run_extraction_pipeline.py` 支持批量 .txt → LLM 抽取 → Neo4j 入库 |
| Streamlit 问答 | ✅ 可用 | `app.py` 实时连接 Neo4j，支持自然语言查询 |
| 真实数据 | ⚡ 进行中 | 可通过爬虫采集，已支持 30+ 条事故批量入库验证 |
| PDF 解析 / OCR | ⏳ 待实现 | pdfplumber 集成待填充，扫描 PDF 需 PaddleOCR |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量（编辑 .env，填入 LLM_API_KEY 和 Neo4j 密码）
#    .env.example 中有模板

# 3. 初始化数据库
python scripts/init_db.py

# 4a. 端到端演示（样本数据 → Neo4j → 问答）
python scripts/run_demo_pipeline.py

# 4b. 或：爬取真实事故数据 + 批量构建 KG（二选一）
python -c "from src.acquisition.report_crawler import ReportCrawler; ReportCrawler().run(max_reports=50)"
python scripts/run_extraction_pipeline.py --input data/raw/accident_reports

# 5. 启动 Web 问答界面
streamlit run app.py
```

## 数据采集

系统目前可用的数据源：

| 数据源 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| **ciedu.com.cn** 事故案例库 | P0 | ⚠️ 浏览器可访问（requests 被挡） | 1950-2026 年完整调查报告原文，含 PDF 附件，质量极高 |
| **mem.gov.cn** 历史上的危化品事故 | P1 | ✅ 已实现 | 94 个月度页，每页 17-41 起事故，含根因分析 |
| **CSB** (美国化学品安全委员会) | P2 | ✅ 已实现 (requests) | 已完成调查列表，JS 渲染需 browser tool 补全 |
| **PubChem** 化学品物性 | P0 | ✅ 已实现 | 20 种危化品，无需 API Key |
| **Open-Meteo** 气象数据 | P0 | ✅ 已实现 | 全球历史天气，1940 年起，无需 Key |
| ichemsafe.com | P2 | ❌ 需登录 | 待评估 |
| ichemsafe.com | P2 | ❌ 需登录 | 待评估 |

### 爬虫运行

```bash
python -c "
from src.acquisition.report_crawler import ReportCrawler
c = ReportCrawler()
c.run(max_reports=200)    # 修改数字控制采集量
"
```

事故文本自动保存到 `data/raw/accident_reports/`，随后可喂给抽取流水线。

## 系统架构

```
Streamlit Web 应用层 (问答 + 可视化)
┃  Graph RAG 问答层 (因果约束 LLM 生成)
┃  知识存储层 (Neo4j + SQLite)
┃  LLM 知识抽取层 (DeepSeek API + Prompt Chain)
┃  数据获取与预处理层 (爬虫 + PDF解析)
```

## 目录结构

```
ChemSafe-KG/
├── app.py                     # Streamlit 应用入口（问答/分析/管理）
├── pipeline.py                # 流水线编排器
├── config/                    # 全局配置 (LLM/DB/路径/爬虫)
│   ├── settings.py            # 统一配置入口
│   ├── database.py            # SQLAlchemy 引擎与 Session 管理
│   └── llm_config.py          # LLM API 客户端工厂
├── src/
│   ├── acquisition/           # 数据获取
│   │   ├── report_crawler.py  # ★ 事故报告爬虫 (mem.gov.cn / CSB)
│   │   ├── chemical_api.py    # 化学品物性 (PubChem)
│   │   └── weather_fetcher.py # 气象数据 (Open-Meteo)
│   ├── preprocessing/         # 数据预处理 (PDF/清洗/融合)
│   ├── extraction/            # ★ LLM 知识抽取 (Prompt Chain)
│   ├── storage/               # 知识存储 (Neo4j + SQLite)
│   ├── retrieval/             # Graph RAG 检索
│   ├── qa/                    # ★ 因果约束问答
│   └── visualization/         # 可视化
├── scripts/
│   ├── run_demo_pipeline.py   # ★ 端到端演示流水线
│   ├── run_extraction_pipeline.py  # ★ 批量知识抽取流水线
│   ├── init_db.py             # 数据库初始化
│   └── seed_data.py           # 种子数据插入
├── data/
│   ├── raw/
│   │   └── accident_reports/  # 爬虫下载的事故报告文本
│   ├── processed/             # 处理后数据
│   └── external/              # 外部引用数据
├── docs/
│   └── framework-guide.md     # 详细说明文档
└── requirements.txt           # Python 依赖
```

## 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| 图数据库 | Neo4j 5.26.25 + py2neo | 知识图谱存储与因果路径查询 |
| 关系数据库 | SQLite + SQLAlchemy | 结构化数据存储 |
| LLM服务 | DeepSeek deepseek-v4-flash | 实体抽取、答案生成 |
| 前端 | Streamlit + Plotly | 交互式 Web 应用 |
| 数据处理 | Pandas + NumPy + jieba | 数据清洗与中文分词 |
| 数据采集 | requests + BeautifulSoup | 网络爬虫 (mem.gov.cn) |
| 化学品API | PubChem PUG REST (免费) | 物性数据查询 |
| 气象API | Open-Meteo (免费) | 历史天气数据查询 |

## 运行验证

```bash
# 检查 LLM API
python -c "from config.llm_config import get_llm_client; print([m.id for m in get_llm_client().models.list()])"

# 检查 Neo4j
python -c "from py2neo import Graph; g=Graph('bolt://localhost:7687',auth=('neo4j','chemsafe123')); print(g.run('MATCH (n) RETURN count(n)').data())"

# 爬虫验证
python -c "from src.acquisition.report_crawler import ReportCrawler; print('爬虫就绪')"

# 端到端演示
python scripts/run_demo_pipeline.py
```

## 开发计划

| 周次 | 任务 | 当前进度 |
|------|------|---------|
| 9-10 | 环境配置 + 技术选型 | ✅ 完成 |
| 11 | 数据采集爬虫实现 | ✅ 完成（mem.gov.cn 94页） |
| 12-13 | LLM 抽取 + Neo4j + Graph RAG + 前端 | ✅ **全部完成，进度超前** |
| 14 | 数据扩充 + 多源融合 + EDA | ⚡ 进行中 |
| 15 | 可视化完善 + 性能优化 + 融合分析 | 🔲 待开始 |
| 16 | 集成测试 + 报告撰写 + 演示准备 | 🔲 待开始 |

## 详细文档

详见 [框架说明文档](docs/framework-guide.md)，包含：
- 五层架构详解（每层的模块接口、当前状态、TODO清单）
- 27项待办按 P0/P1/P2/P3 优先级分组
- 外部数据源与资源清单（含 URL）

## 项目成员

- 翟彝凡（化工系）
- 余亮阳（化工系）
- 赵乐毅（化工系）

指导老师：王健楠 教授

本项目仅用于课程学习目的。
