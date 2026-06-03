# ChemSafe-KG 项目框架说明文档

> **项目**：ChemSafe-KG：基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统  
> **框架版本**：v0.5.0（200 份事故数据 + 统计仪表盘 + 因果路径可视化 + 多源融合就绪）  
> **编写时间**：2026-06-04（最后修订）

---

## 目录

1. [项目概述](#1-项目概述)
2. [目录结构总览](#2-目录结构总览)
3. [五层架构详解](#3-五层架构详解)
   - 3.1 数据获取与预处理层
   - 3.2 LLM驱动的知识抽取层
   - 3.3 知识存储与融合层
   - 3.4 Graph RAG检索层
   - 3.5 因果推理问答生成层
   - 3.6 前端可视化层
4. [核心模块接口说明](#4-核心模块接口说明)
5. [待完善与补充部分清单](#5-待完善与补充部分清单)
6. [快速开始指南](#6-快速开始指南)
7. [技术债务与风险说明](#7-技术债务与风险说明)

---

## 1. 项目概述

### 1.1 项目目标

构建一个端到端的化工安全事故知识图谱系统，实现：

- **自动化 KG 构建**：利用 LLM 从非结构化事故报告中抽取实体与因果关系，构建知识图谱
- **因果约束问答**：基于知识图谱中的因果链，约束 LLM 的答案生成，避免幻觉
- **多源数据融合**：融合事故数据、化学品物性数据、气象数据进行多维分析

### 1.2 技术栈

| 层次 | 技术组件 | 用途 |
|------|---------|------|
| 数据采集 | requests, BeautifulSoup, pdfplumber | 爬取/解析事故报告 |
| 数据处理 | Pandas, NumPy, jieba | 清洗、分词、融合 |
| 图数据库 | Neo4j Community 5.x + py2neo | 知识图谱存储与查询 |
| 关系数据库 | SQLite (开发) / PostgreSQL (生产) + SQLAlchemy | 结构化数据存储 |
| LLM服务 | DeepSeek API (OpenAI 兼容协议) | 实体抽取、答案生成 |
| RAG框架 | LangChain (部分组件引用) | Graph RAG 流水线编排 |
| 前端展示 | Streamlit + Plotly + streamlit-agraph | Web交互与可视化 |
| 项目配置 | python-dotenv + 分层配置类 | 环境管理与配置 |

---

## 2. 目录结构总览

```
ChemSafe-KG/
│
├── app.py                          # Streamlit Web 应用入口
├── pipeline.py                     # 主流水线编排器（全流程调度）
├── requirements.txt                # Python 依赖清单
├── .env.example                    # 环境变量模板（复制为 .env 使用）
├── .gitignore                      # Git 忽略规则
│
├── config/                         # 全局配置层
│   ├── __init__.py
│   ├── settings.py                 # 统一配置入口（LLM / DB / 路径 / 爬虫）
│   ├── database.py                 # SQLAlchemy 引擎与 Session 管理
│   └── llm_config.py               # LLM API 客户端工厂
│
├── src/                            # 核心源码
│   ├── acquisition/                # [层1] 数据获取
│   │   ├── report_crawler.py       #   事故报告爬虫
│   │   ├── chemical_api.py         #   化学品物性 API 客户端
│   │   └── weather_fetcher.py      #   气象数据获取器
│   │
│   ├── preprocessing/              # [层1续] 数据预处理
│   │   ├── pdf_parser.py           #   PDF 解析器
│   │   ├── text_cleaner.py         #   文本清洗与标准化
│   │   └── data_merger.py          #   多源数据融合
│   │
│   ├── extraction/                 # [层2] LLM 知识抽取（核心创新①）
│   │   ├── llm_client.py           #   LLM API 统一封装
│   │   ├── prompt_templates.py     #   Prompt Chain 模板
│   │   ├── entity_extractor.py     #   实体关系抽取引擎
│   │   ├── result_validator.py     #   抽取结果验证
│   │   └── multimodal_parser.py    #   [可选] P&ID 流程图解析
│   │
│   ├── storage/                    # [层3] 知识存储
│   │   ├── neo4j_client.py         #   Neo4j 连接与操作
│   │   ├── schema_manager.py       #   图 Schema 管理
│   │   ├── relational_db.py        #   关系数据库 ORM 模型
│   │   └── data_linker.py          #   跨模态数据链接
│   │
│   ├── retrieval/                  # [层4] Graph RAG 检索
│   │   ├── query_analyzer.py       #   自然语言问题分析
│   │   ├── entity_linker.py        #   实体链接
│   │   ├── cypher_generator.py     #   Cypher 查询生成
│   │   └── causal_path_retriever.py #   因果路径检索
│   │
│   ├── qa/                         # [层5] 问答生成
│   │   ├── context_builder.py      #   RAG 上下文构建
│   │   ├── answer_generator.py     #   答案生成（LLM约束）
│   │   └── fallback_handler.py     #   降级处理
│   │
│   └── visualization/              # [层6] 前端可视化
│       ├── kg_visualizer.py        #   知识图谱可视化
│       ├── stats_dashboard.py      #   统计分析仪表板
│       └── causal_path_viz.py      #   因果路径可视化
│
├── scripts/                        # 工具脚本
│   ├── init_db.py                  # 数据库初始化
│   ├── seed_data.py                # 种子数据插入（含 LLM 抽取入库）
│   ├── run_demo_pipeline.py        # ★ 端到端演示流水线
│   ├── run_extraction_pipeline.py  # ★ 批量知识抽取流水线
│   └── enrich_data.py              # ★ 数据充实（化学品+气象+融合视图）
│
├── data/                           # 数据目录
│   ├── raw/                        #   原始数据（.gitkeep 占位）
│   ├── processed/                  #   处理后的数据
│   └── external/                   #   外部引用数据
│
├── docs/                           # 文档
│   └── framework-guide.md          #   本文件
│
└── tests/                          # 测试目录（待填充）
```

---

## 3. 五层架构详解

### 3.1 数据获取与预处理层

**目录**：`src/acquisition/` + `src/preprocessing/`

**职责**：从多源获取原始数据，清洗并融合为结构化格式。

#### 当前实现

| 模块 | 文件 | 实现状态 | 说明 |
|------|------|---------|------|
| 事故报告爬虫 | `report_crawler.py` | ✅ **已实现** | 200 份 mem.gov.cn 事故报告已采集 |
| 化学品API | `chemical_api.py` | ✅ 已实现 | 29 种危化品物性（PubChem via pubchempy） |
| 气象数据 | `weather_fetcher.py` | ✅ 已实现 | Open-Meteo，免费无需 Key |
| PDF解析 | `pdf_parser.py` | ⏳ 基础实现 | pdfplumber 单文件可解析，未接入批量流水线 |
| 文本清洗 | `text_cleaner.py` | ✅ 已实现 | 空白规范化、标点标准化、页眉页脚去除、PII 脱敏、智能分段 |
| 数据融合 | `data_merger.py` | ✅ 已实现 | 事故-化学品关联 + 气象关联 + 统一视图构建 |

#### TODO 清单（更新于 v0.5.0）

爬虫模块 ✅ 已实现：
- [x] mem.gov.cn 列表页解析（95 条月度汇编）
- [x] 月度详情页事故提取（逐段扫描，特征区分）
- [x] URL 正确拼接（urljoin 处理相对路径）
- [x] 批量限制（max_reports 参数）
- [x] CSB 列表页解析（requests 降级）
- [x] 文件保存为 UTF-8 .txt
- [x] 批量抽取流水线（.txt → LLM → Neo4j + SQLite）

仍待完成：
- [ ] 其他数据源接入（ciedu.com.cn 502、ichemsafe.com 需登录）
- [ ] 扫描 PDF OCR（PaddleOCR/Tesseract 集成）
- [ ] EPA CompTox API 接入（需注册免费 Key）

---

### 3.2 LLM驱动的知识抽取层（核心创新点①）

**目录**：`src/extraction/`

**职责**：设计 Prompt Chain 策略，驱动 LLM 从非结构化文本中提取实体和因果关系。

#### 已有骨架

| 模块 | 文件 | 说明 |
|------|------|------|
| LLM客户端 | `llm_client.py` | `LLMClient` 类，基于 OpenAI SDK 封装，支持重试和 JSON 模式 |
| Prompt模板 | `prompt_templates.py` | `PromptTemplates` 类，包含 System Prompt、抽取指令、验证 Prompt |
| 抽取引擎 | `entity_extractor.py` | `EntityExtractor` 类，文本→JSON→三元组的完整流程 |
| 结果验证 | `result_validator.py` | `ResultValidator` 类，结构验证、类型校验、置信度评分 |
| 多模态解析 | `multimodal_parser.py` | `MultimodalParser` 类，P&ID 流程图识别骨架 |

Prompt 设计示例已在 `prompt_templates.py` 中完整定义，包含：
- **System Prompt**：化工过程安全专家角色设定
- **实体类型**：Equipment, Material, Abnormal_Condition, Consequence, Mitigation
- **关系类型**：leads_to, involves, mitigated_by
- **输出格式**：严格的 JSON Schema 约束（event_chain + root_cause + consequence）

#### TODO 清单

- [x] LLM API Key 已配置：DeepSeek `deepseek-v4-flash`
- [x] LLM 连接测试通过：`chat()` 和 `chat_json()` 正常
- [x] Prompt Chain 已验证：5 类实体 / 3 类关系 + Few-shot 示例
- [x] 批量抽取通过：200 份报告，174 成功，995 条三元组
- [ ] PDF 分段抽取合并：超长报告的分段-合并策略
- [ ] 并发抽取：asyncio 加速
- [ ] 同义实体合并：抽取结果去重

---

### 3.3 知识存储与融合层

**目录**：`src/storage/`

**职责**：将抽取的结构化数据存入 Neo4j 图数据库和关系数据库，并实现跨源链接。

#### 已有骨架

| 模块 | 文件 | 说明 |
|------|------|------|
| Neo4j 客户端 | `neo4j_client.py` | `Neo4jClient` 类，连接管理、节点/关系创建、路径查询 |
| Schema管理 | `schema_manager.py` | `GraphSchema` 类，节点标签、关系类型、索引约束定义 |
| 关系数据库 | `relational_db.py` | SQLAlchemy ORM 模型：AccidentRecord, ChemicalProperty, WeatherRecord |
| 数据链接 | `data_linker.py` | `DataLinker` 类，KG↔SQL 跨源链接 |

#### TODO 清单

- [x] Neo4j 5.26.25 已安装运行
- [x] Neo4j 连接已配置（bolt://localhost:7687）
- [x] 数据库索引/约束已创建（UNIQUE 约束防重复节点）
- [x] ORM 模型完整：AccidentRecord + ChemicalProperty + WeatherRecord
- [x] 批量写入已验证：995 条三元组成功入库
- [ ] 跨源链接完善：Neo4j↔SQLite 数据联动（data_linker.py）

---

### 3.4 Graph RAG 检索层

**目录**：`src/retrieval/`

**职责**：理解用户自然语言问题，在知识图谱中检索相关因果路径。

#### 已有骨架

| 模块 | 文件 | 说明 |
|------|------|------|
| 查询分析 | `query_analyzer.py` | `QueryAnalyzer` 类，意图识别 + 关键词提取（基于规则） |
| 实体链接 | `entity_linker.py` | `EntityLinker` 类，实体名→图节点匹配 |
| Cypher生成 | `cypher_generator.py` | `CypherGenerator` 类，按意图模板生成查询语句 |
| 路径检索 | `causal_path_retriever.py` | `CausalPathRetriever` 类，执行查询并格式化为文本 |

#### TODO 清单

- [x] 因果路径检索可执行 Cypher 查询
- [x] 上下文格式化（结构化的因果链文本）
- [x] jieba 分词集成 + 实体提取
- [x] 三级实体匹配：精确 → 包含 → 嵌入语义（sentence-transformers）
- [x] query_analyzer 意图检测 + 关键词提取
- [ ] cypher_generator 查询模板完善（mitigation/statistics 类型）

---

### 3.5 因果推理问答生成层（核心创新点②）

**目录**：`src/qa/`

**职责**：在知识图谱因果路径的约束下，调用 LLM 生成严格遵循事实的回答。

#### 已有骨架

| 模块 | 文件 | 说明 |
|------|------|------|
| 上下文构建 | `context_builder.py` | `ContextBuilder` 类，RAG 系统 Prompt + 用户 Prompt 组合 |
| 答案生成 | `answer_generator.py` | `AnswerGenerator` 类，LLM 调用 + 降级响应 |
| 降级处理 | `fallback_handler.py` | `FallbackHandler` 类，全文检索降级 + 模板应答 |

#### TODO 清单

- [x] LLM 答案生成已验证（DeepSeek API + Graph RAG 约束）
- [x] 降级处理：LLM 失败时返回原始因果路径
- [ ] 答案引用来源标注：标注每条陈述对应的因果路径
- [ ] 上下文窗口管理：超长检索结果截断/摘要
- [ ] 全文检索降级：文本倒排索引

---

### 3.6 前端可视化层

**目录**：`src/visualization/` + `app.py`

**职责**：提供基于 Streamlit 的 Web 交互界面，包括问答、图谱浏览、数据分析。

#### 已有骨架

| 模块 | 文件 | 说明 |
|------|------|------|
| KG可视化 | `kg_visualizer.py` | `KGFrontendVisualizer` 类，Neo4j→vis.js 数据转换 |
| 统计仪表板 | `stats_dashboard.py` | `StatsDashboard` 类，Plotly 图表生成（时间线、风险矩阵等） |
| 因果路径图 | `causal_path_viz.py` | `CausalPathVisualizer` 类，单条因果链的流程图可视化 |
| Web应用 | `app.py` | Streamlit 多页面应用，含导航、问答界面、管理面板 |

#### TODO 清单

- [x] Streamlit 问答页面：实时连接 Neo4j，调用 QA 流水线
- [x] 统计仪表盘：8 种图表（trends/pie/bar/scatter/sankey/location）
- [x] 因果路径可视化：单条/多条路径的有向图渲染，集成到图谱浏览页
- [x] KG 全局可视化：streamlit-agraph 渲染，节点类型着色
- [ ] 节点度中心性调节大小 + 交互式下钻

---

## 4. 核心模块接口说明

### 4.1 主要类的构造与调用关系

```
app.py (Streamlit)
  └── AnswerGenerator.generate(question, causal_context)
        ├── ContextBuilder.build(question, context) → (sys_prompt, user_prompt)
        └── LLMClient.chat(system_prompt, user_prompt)
              └── OpenAI SDK → DeepSeek API

pipeline.py
  ├── Stage 1: ReportCrawler.run()
  │              └── PDFParser.parse(pdf_path)
  │                   └── TextCleaner.clean_report_text(text)
  │
  ├── Stage 2: EntityExtractor.extract_batch(chunks)
  │              ├── PromptTemplates.format_extraction_prompt(text)
  │              ├── LLMClient.chat_json(system, user)
  │              └── ResultValidator.validate_structure(result)
  │
  └── Stage 3: Neo4jClient.batch_create_triples(triples)
                   └── GraphSchema.create_index_constraints(graph)
```

### 4.2 关键数据流格式

**输入**：事故报告 PDF → 纯文本 → 清洗后的文本片段

**中间格式**（LLM 抽取输出）：
```json
{
  "event_chain": [
    {"entity": "冷却水循环泵", "type": "Equipment", "status": "故障"},
    {"relation": "leads_to", "target": "储罐温度上升"},
    {"entity": "储罐温度上升", "type": "Abnormal_Condition"},
    ...
  ],
  "root_cause": "冷却水循环泵故障",
  "consequence": "储罐爆炸，丙烯腈泄漏"
}
```

**存储格式**：(subject, relation, object) 三元组 → Neo4j 节点和关系

**查询响应**：Cypher 查询结果 → 文本上下文 → LLM 生成的回答

---

## 5. 待完善与补充部分清单

### 5.1 按优先级分组

#### 🔴 P0 — 必须优先完成（项目可运行的基础）

| 编号 | 待办项 | 状态 |
|------|--------|------|
| 1 | LLM API Key（DeepSeek） | ✅ 已完成 |
| 2 | Neo4j 安装启动 | ✅ 已完成 (5.26.25) |
| 3 | Neo4j 连接配置 | ✅ 已完成 |
| 4 | LLM API 连通性测试 | ✅ 已完成 |
| 5 | Neo4j 连接测试 | ✅ 已完成 |
| 6 | Python 依赖安装 | ✅ 已完成 |

#### 🟡 P1 — 重要功能（核心业务逻辑）

| 编号 | 待办项 | 状态 |
|------|--------|------|
| 7 | 爬虫页面解析 | ✅ 已完成（mem.gov.cn 200 份） |
| 8 | PDF 文本提取 | ⏳ 基础实现，未接入批量 |
| 9 | LLM 实体抽取 | ✅ 已完成（174/200 成功） |
| 10 | 三元组→Neo4j 写入 | ✅ 已完成 |
| 11 | Cypher 查询生成 | ⏳ 基础实现，待完善 |
| 12 | 问答流水线串联 | ✅ 已完成 |
| 13 | 前端问答交互 | ✅ 已完成 |

#### 🟢 P2 — 增强功能（提升质量和体验）

| 编号 | 待办项 | 状态 |
|------|--------|------|
| 14 | 扩充爬虫数据源 | ✅ 已完成（9 个 URL） |
| 15 | 化学品物性 API | ✅ 已完成（29 种，PubChem） |
| 16 | 气象数据获取 | ✅ 已完成（Open-Meteo） |
| 17 | 扫描 PDF OCR | ❌ 未实现 |
| 18 | 统计仪表盘 | ✅ 已完成（stats_dashboard.py） |
| 19 | KG 可视化 | ✅ 已完成（streamlit-agraph） |
| 20 | Prompt 模板优化 | ✅ 已完成（Few-shot + 5 规则） |

#### 🔵 P3 — 锦上添花（可选加分项）

| 编号 | 待办项 | 状态 |
|------|--------|------|
| 21 | 多模态 P&ID 图识别 | ❌ 未实现 |
| 22 | 全文检索降级 | ⏳ 骨架已定义 |
| 23 | 多源数据融合分析 | ✅ 已完成（DataMerger） |
| 24 | Docker 部署配置 | ❌ 未实现 |
| 25 | 单元测试 | ❌ 未实现 |
| 26 | 事故风险预测（ML） | ❌ 未实现 |

### 5.2 外部数据源与资源清单

以下资源从 [材料.md](../材料.md) 整理，按模块和优先级分类。

#### 🔴 事故报告数据源

| 优先级 | 资源名称 | URL | 说明 |
|--------|---------|-----|------|
| **P0** | 化工安全教育平台 - 事故案例 | `https://ciedu.com.cn` | ❌ 网站502不可达 |
| **P1** | 应急管理部 - 历史上的危化品事故 | `https://www.mem.gov.cn/fw/jsxx/lssdwhpsg/` | ✅ **已实现** — 94个月度页，每页17-41起事故 |
| P1 | 中国化学品安全协会 - 事故案例库 | `https://www.chemicalsafety.org.cn/shiguxinxi/shiguanli` | ⏳ URL已填入，解析待实现 |
| P1 | 应急管理部 - 政府信息公开 | `http://www.mem.gov.cn` | ✅ URL已填入 |
| P2 | CSB 调查报告 | `https://www.csb.gov/investigations/` | ✅ URL已填入 |
| P2 | CSB Incident Reports | `https://www.csb.gov/incident-reports/` | ✅ URL已填入 |
| P2 | ChemSafe 事故案例库 | `https://www.ichemsafe.com` | ✅ URL已填入 |
| P2 | NTSB 事故调查 | `https://www.ntsb.gov` | ✅ URL已填入 |
| P2 | eMARS 欧盟事故数据库 | `https://emars.jrc.ec.europa.eu` | ✅ URL已填入 |

**当前策略**：
- **ciedu.com.cn** — ⚠️ 浏览器可访问，内容质量极高（完整调查报告原文），但反爬严格（CAPTCHA），需 browser tool 实现。适合中期汇报后接入。
- **mem.gov.cn** — ✅ 当前主数据源，94 个月度汇编页（2018 ~ 2026），每页 17~41 起事故，含完整根因分析。

#### 🟢 化学品物性数据库

| 优先级 | 资源名称 | URL | API Key | 说明 |
|--------|---------|-----|---------|------|
| **P0** | PubChem PUG REST | `https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest` | 无需 | ✅ 已在 `chemical_api.py` 中实现 |
| P1 | EPA CompTox Dashboard | `https://comptox.epa.gov/dashboard` | 免费注册 | 备用，需在 `.env` 配置 `EPA_API_KEY` |
| P2 | eChemPortal (OECD) | `https://www.echemportal.org` | 无需 | 多国监管数据聚合 |

#### 🔵 气象数据源

| 优先级 | 资源名称 | URL | API Key | 说明 |
|--------|---------|-----|---------|------|
| **P0** | Open-Meteo Archive API | `https://open-meteo.com` | 无需 | ✅ 已在 `weather_fetcher.py` 中实现，历史数据自1940年 |
| P2 | NOAA NCEI | `https://www.ncei.noaa.gov/access` | 无需 | 备用 |
| P2 | 中国气象数据网 | `http://data.cma.cn` | 免费注册 | 中国站点数据 |
| P2 | APiHZ 历史天气 | `https://cn.apihz.cn` | 免费 | 国内站点补充 |

#### 🟣 开发工具与平台

| 资源 | URL | 用途 |
|------|-----|------|
| DeepSeek 开放平台 | `https://platform.deepseek.com` | 注册获取 API Key，按量计费，成本较低 |
| 智谱AI (ChatGLM) | `https://open.bigmodel.cn` | 备用 LLM 服务 |
| Neo4j 下载 | `https://neo4j.com/download-center/#community` | 图数据库 (需 JDK 17) |
| Neo4j APOC | `https://github.com/neo4j/apoc` | 图数据处理扩展库 |
| LangChain Graph RAG | `https://docs.langchain.com/oss/python/langchain/graph-rag` | Graph RAG 集成方案 |
| Tesseract OCR | `https://github.com/tesseract-ocr/tesseract` | OCR 引擎 |
| PaddleOCR | `https://github.com/PaddlePaddle/PaddleOCR` | 中文 OCR |

#### 📦 Python 核心依赖

| 库 | 安装 | 用途 |
|---|------|------|
| pdfplumber | `pip install pdfplumber` | PDF 文本和表格提取 |
| py2neo | `pip install py2neo` | Neo4j 连接 |
| pubchempy | `pip install pubchempy` | PubChem API Python 封装 |
| streamlit-agraph | `pip install streamlit-agraph` | 知识图谱可视化 (vis.js) |
| plotly | `pip install plotly` | 交互式图表 |
| jieba | `pip install jieba` | 中文分词 |
| openai | `pip install openai` | DeepSeek API 调用 (OpenAI 协议) |

#### ✅ 当前状态总览

| 资源/功能 | 用途 | 当前状态 |
|-----------|------|----------|
| DeepSeek API Key / deepseek-v4-flash | LLM 抽取 + 问答生成 | ✅ 已配置并验证 |
| Neo4j 5.26.25 | 图数据库 | ✅ 已安装运行，Schema 已初始化 |
| 端到端流水线 (`run_demo_pipeline.py`) | 样本数据抽取→存储→检索→问答 | ✅ 已验证通过 |
| Streamlit Web 问答页面 | 自然语言交互 | ✅ 可实时查询 Neo4j |
| 化学品物性 API (PubChem) | 物性数据获取 | ✅ 已实现（无需 Key） |
| 气象数据 API (Open-Meteo) | 天气数据获取 | ✅ 已实现（无需 Key） |
| 事故数据源 URL | 爬虫配置 | ✅ 8 个网址已填入 |
| mem.gov.cn 爬虫 | HTML 列表提取 + 事故解析 | ✅ 200+ 份报告已采集 |
| 真实事故报告数据 | 构建完整 KG | ✅ 200 份，批量抽取中 |
| 统计仪表盘 | 事故多维分析 | ✅ 已实现（trends/pie/bar/sankey） |
| 因果路径可视化 | 路径有向图渲染 | ✅ 已实现（单条/多条/Neo4j集成） |
| 多源数据融合 | 事故-化学品-气象关联 | ✅ 已实现（DataMerger + enrich_data） |
| EPA CompTox API (可选) | 化学品补充数据 | ❌ 未获取 Key |

---

## 6. 快速开始指南

### 6.1 环境准备

```bash
# 1. 克隆项目
cd ChemSafe-KG

# 2. 创建虚拟环境
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
# 编辑 .env，填入 LLM_API_KEY 和 Neo4j 连接信息
# （已配置: DeepSeek deepseek-v4-flash + Neo4j localhost:7687）

# 5. 确保 Neo4j 已启动
# 浏览器访问 http://localhost:7474 确认

# 6. 初始化数据库
python scripts/init_db.py
```

### 6.2 运行演示（推荐）

```bash
# 端到端流水线演示（抽取→存储→检索→问答）
python scripts/run_demo_pipeline.py

# 启动 Streamlit Web 问答应用
streamlit run app.py
```

### 6.3 验证安装

```bash
# 检查依赖安装
python -c "import pandas; import py2neo; import streamlit; print('Dependencies OK')"

# 检查 LLM API
python -c "from config.llm_config import get_llm_client; print('LLM OK:', [m.id for m in get_llm_client().models.list()])"

# 检查 Neo4j 连接
python -c "from py2neo import Graph; g=Graph('bolt://localhost:7687',auth=('neo4j','chemsafe123')); print('Neo4j OK:', g.run('MATCH (n) RETURN count(n)').data()[0])"

---

## 7. 技术债务与风险说明

### 7.1 当前框架状态

- ✅ **目录结构**：完整搭建，模块划分清晰
- ✅ **类/接口设计**：核心类的构造、方法签名已定义
- ✅ **配置体系**：分层配置，支持 `.env` 环境管理
- ✅ **数据模型**：图 Schema 和关系表模型已设计
- ✅ **流水线编排**：`pipeline.py` 支持分阶段执行
- ✅ **爬虫模块**：`report_crawler.py` mem.gov.cn 解析器已实现（94个月度页，2000+事故）
- ✅ **批量抽取流水线**：`scripts/run_extraction_pipeline.py` 已完成，支持.txt→LLM→Neo4j
- ✅ **数据源URL**：9 个事故数据源 URL 已填入代码
- ✅ **PubChem API**：`chemical_api.py` 已实现真实调用（无需 Key）
- ✅ **气象数据**：`weather_fetcher.py` 已集成 Open-Meteo（免费，无需 Key）
- ✅ **LLM API**：DeepSeek `deepseek-v4-flash` 已验证可调用
- ✅ **Neo4j 5.26.25**：已安装运行，Schema 已初始化
- ✅ **SQLite 数据库**：表结构已创建
- ✅ **因果路径查询**：`find_causal_paths()` 可实际执行 Cypher 查询
- ✅ **上下文格式化**：`format_context()` 可将路径转换为结构化文本
- ✅ **端到端流水线**：`scripts/run_demo_pipeline.py` 已验证通过
- ✅ **Pipeline CLI**：`pipeline.py` 接入所有真实模块（acquisition/extraction/enrich/qa）
- ✅ **化学品物性**：29 种危化品物性（PubChem via pubchempy）
- ✅ **统计仪表盘**：`stats_dashboard.py` 完整实现（8 种图表类型）
- ✅ **因果路径可视化**：`causal_path_viz.py` 支持单条/多条路径的有向图渲染
- ✅ **多源数据融合**：`data_merger.py` 实现事故-化学品-气象关联逻辑
- ✅ **统一融合视图**：200 行 × 19 列，化学品覆盖 8.5%
- ✅ **QA 验证通过**：有限空间→中毒窒息问题给出高质量因果推理回答
- ⏳ **PDF 解析**：`pdf_parser.py` 已有基础实现，待集成到批量流水线
- ❌ **其他数据源爬虫**：ciedu.com.cn(502)、ichemsafe.com(需登录) 待实现

### 7.2 关键风险

| 风险 | 影响 | 应对 |
|------|------|------|
| LLM API 调用费用 | 可能需要预算 | ✅ 已配置，控制调用量（先小批量测试） |
| Neo4j 环境配置 | 开发初期阻塞 | ✅ 已解决，5.26.25 已运行 |
| 爬虫数据源不可用 | 核心数据缺失 | mem.gov.cn 已解决，主数据源可用 |
| LLM 抽取质量低 | KG 质量不达标 | Prompt 迭代 + 人工抽样验证 |

### 7.3 推荐的开发顺序

1. **第9-10周（已完成）**：环境配置 ✅ | 技术选型 ✅
2. **第11周（已完成）**：爬虫实现 ✅ | mem.gov.cn 200 份报告 ✅
3. **第12-13周（已完成）**：LLM 抽取 ✅ | Neo4j 入库 ✅ | 批量流水线 ✅
4. **第14周（已完成）**：Graph RAG 检索 ✅ | 问答生成 ✅ | 前端串联 ✅
5. **第15周（已完成）**：数据扩充 ✅ | 统计仪表盘 ✅ | 因果路径可视化 ✅ | 多源融合 ✅
6. **第16周（当前）**：文档完善 → QA 增强 → 演示准备 → 课程报告

---

*本文档会随项目进度持续更新。每次完成一个 TODO 项后，请在对应位置标记完成。*
