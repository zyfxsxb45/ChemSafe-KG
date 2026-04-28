# ChemSafe-KG

> **基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统**  
> 数据库技术及应用课程项目 · 大二下  
> **当前状态：v0.3.0 — 端到端流水线已验证通过**

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
| 端到端流水线 | ✅ 验证通过 | 样本数据抽取→存储→检索→问答全链路已跑通 |
| Streamlit 问答 | ✅ 可用 | `app.py` 实时连接 Neo4j，支持自然语言查询 |
| 数据采集 | ⏳ 待填充 | 爬虫页面解析逻辑待实现 |
| 真实数据 | ❌ 未采集 | 当前仅有 2 条 LLM 抽取的样本数据（16节点/15关系） |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
python scripts/init_db.py

# 3. 运行端到端演示（样本数据 → Neo4j → 问答）
python scripts/run_demo_pipeline.py

# 4. 启动 Web 问答界面
streamlit run app.py
```

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
├── app.py                 # Streamlit 应用入口（问答/分析/管理）
├── pipeline.py            # 流水线编排器
├── config/                # 全局配置 (LLM/DB/路径/爬虫)
├── src/
│   ├── acquisition/       # 数据获取 (爬虫/PubChem/气象)
│   ├── preprocessing/     # 数据预处理 (PDF/清洗/融合)
│   ├── extraction/        # LLM 知识抽取 ★
│   ├── storage/           # 知识存储 (Neo4j + SQL)
│   ├── retrieval/         # Graph RAG 检索
│   ├── qa/                # 因果约束问答 ★
│   └── visualization/     # 可视化
├── scripts/
│   ├── run_demo_pipeline.py  # ★ 端到端演示流水线
│   ├── init_db.py            # 数据库初始化
│   └── seed_data.py          # 种子数据插入
├── data/                  # 数据目录
└── docs/framework-guide.md # 详细说明文档
```

## 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| 图数据库 | Neo4j 5.26.25 + py2neo | 知识图谱存储与因果路径查询 |
| 关系数据库 | SQLite + SQLAlchemy | 结构化数据存储 |
| LLM服务 | DeepSeek deepseek-v4-flash | 实体抽取、答案生成 |
| 前端 | Streamlit + Plotly | 交互式 Web 应用 |
| 数据处理 | Pandas + NumPy + jieba | 数据清洗与中文分词 |
| 数据采集 | requests + BeautifulSoup | 网络爬虫（待实现） |
| 化学品API | PubChem PUG REST (免费) | 物性数据查询 |
| 气象API | Open-Meteo (免费) | 历史天气数据查询 |

## 运行验证

```bash
# 检查 LLM API
python -c "from config.llm_config import get_llm_client; print([m.id for m in get_llm_client().models.list()])"

# 检查 Neo4j
python -c "from py2neo import Graph; g=Graph('bolt://localhost:7687',auth=('neo4j','chemsafe123')); print(g.run('MATCH (n) RETURN count(n)').data())"

# 端到端演示
python scripts/run_demo_pipeline.py
```

## 开发计划

| 周次 | 任务 | 当前进度 |
|------|------|---------|
| 9-10 | 环境配置 + 数据采集爬虫 | ⏳ 环境就绪，爬虫待实现 |
| 11 | 数据清洗 + EDA + 多源融合 | 🔲 待开始 |
| 12-13 | LLM 抽取流水线 + Neo4j 入库 | ✅ 框架完成，样本已验证 |
| 14 | Graph RAG 检索 + 问答 + 前端 | ✅ 框架完成，样本已验证 |
| 15 | 真实数据采集 + KG扩充 + 可视化 | 🔲 需爬虫就绪 |
| 16 | 集成测试 + 报告撰写 | 🔲 待开始 |

## 详细文档

详见 [框架说明文档](docs/framework-guide.md)，包含：
- 五层架构详解（每层的模块接口、当前状态、TODO清单）
- 26项待办按 P0/P1/P2/P3 优先级分组
- 外部数据源与资源清单（含 URL）

## 项目成员

- [姓名1]（化工系）
- [姓名2]
- [姓名3]

指导老师：王健楠 教授

本项目仅用于课程学习目的。
