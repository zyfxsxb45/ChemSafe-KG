# ChemSafe-KG 项目框架说明文档

> **项目**：ChemSafe-KG：基于大模型驱动的化工安全事故知识图谱构建与因果推理问答系统  
<<<<<<< HEAD
> **框架版本**：v0.4.1（批量抽取含 SQLite 双写入，30 条真实事故 QA 实测验证通过）  
> **编写时间**：2026-05-21（最后修订）
>>>>>>> 2e7868d (docs: 更新说明文件 (v0.4.1))

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
│   ├── run_demo_pipeline.py        # ★ 端到端演示流水线（核心）
│   ├── run_extraction_pipeline.py  # ★ 批量知识抽取流水线（已实现）
│   ├── init_db.py                  # 数据库初始化
│   └── seed_data.py                # 种子数据插入（含 LLM 抽取入库）
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
| 事故报告爬虫 | `report_crawler.py` | ✅ **已实现** | `fetch_report_list()` 支持 mem.gov.cn 历史上危化品事故栏目，94 个月度汇编页，2000+ 起事故；CSB 列表页基础解析 |
| 化学品API | `chemical_api.py` | ✅ 已实现 | `ChemicalPropertyFetcher`，20 种危化品，PubChem PUG REST API（无需 Key），含 CAS 号查询 |
| 气象数据 | `weather_fetcher.py` | ✅ 已实现 | `WeatherDataFetcher`，Open-Meteo API（免费，无需 Key），含中文地点坐标映射 |
| PDF解析 | `pdf_parser.py` | ❌ 待填充 | pdfplumber 集成待实现，扫描 PDF 需 OCR |
| 文本清洗 | `text_cleaner.py` | ⏳ 骨架 | 空白规范化和分块已完成，页眉页脚去除和脱敏待补充 |
| 数据融合 | `data_merger.py` | ⏳ 骨架 | 接口定义完成，融合逻辑待实现 |

#### TODO 清单（更新于 v0.4.0）

爬虫模块 ✅ 已实现：
- [x] **实现 mem.gov.cn 列表页解析**：5 页列表页，94 条月度汇编链接
- [x] **实现月度详情页事故提取**：逐段扫描 `<div class="cont">`，用特征区分章节/分类/事故标题，提取独立事故及其根因分析
- [x] **实现 URL 正确拼接**：使用 `urljoin()` 处理相对路径 `../202604/...`
- [x] **实现批量限制**：`max_accidents` 参数控制提取量，达到目标提前停止
- [x] **实现 CSB 列表页解析**：CSS 选择器匹配调查卡片（requests 降级）
- [x] **实现文件保存**：自动去除元信息头部，保存为 UTF-8 编码的 .txt 文件
- [x] **实现批量抽取流水线**：`scripts/run_extraction_pipeline.py` 支持目录批量 → LLM 抽取 → Neo4j 入库

仍待完成：
- [ ] **实现爬虫页面解析**：`report_crawler.py` 中其他数据源（ciedu.com.cn 502 不可达，ichemsafe.com 需登录）
  - P2: `https://www.ichemsafe.com` — ChemSafe 事故案例库
  - P2: `https://www.ntsb.gov` — NTSB 事故调查
  - P2: `https://emars.jrc.ec.europa.eu` — eMARS 欧盟事故数据库
- [ ] **实现报告列表解析逻辑**：`fetch_report_list()` 需要基于 BeautifulSoup 实现 HTML 解析（各网站结构需单独分析）
- [ ] **实现 PDF 下载**：`download_report()` 需要处理 HTTP 文件流下载
- [x] **填写 PubChem API 调用**（已实现）：`fetch_from_pubchem()` 使用 PubChem PUG REST API（无需 API Key），可获取分子量、SMILES 等基础属性
- [ ] **填写 EPA API 调用**：`fetch_from_epa()` 需要注册免费 API Key 后实现
- [x] **确定气象数据源**（已选定）：Open-Meteo `https://open-meteo.com`（免费，无需 API Key，历史数据自1940年），已在 `weather_fetcher.py` 中实现
- [ ] **扩充化学品清单**：`TARGET_CHEMICALS` 已扩充至 20 种含 CAS 号的化学品
- [ ] **实现 PDF 文字提取**：`pdf_parser.py` 需要集成 pdfplumber 的 extract_text()
- [ ] **实现扫描 PDF 的 OCR**：为扫描版报告集成 Tesseract 或 PaddleOCR
- [ ] **完善文本清洗规则**：`clean_report_text()` 需要添加页眉页脚去除、敏感信息脱敏

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

- [x] **【关键】配置 LLM API Key**（已完成）：DeepSeek `deepseek-v4-flash`（已验证可调用）
- [x] **测试 LLM 连接**（已验证）：`chat()` 和 `chat_json()` 均可正常返回
- [ ] **Prompt 迭代优化**：用真实事故报告测试 Prompt，调整措辞提高抽取质量
- [ ] **添加 Few-shot 示例**：在 Prompt 模板中加入 1-2 个完整的抽取示例
- [ ] **实现分段抽取合并**：`extract_from_text()` 需要处理超长文本的分段-合并策略
- [ ] **并发抽取**：`extract_batch()` 可改用 asyncio 并发调用加速
- [ ] **抽取结果去重**：`convert_to_triples()` 需要同义实体合并逻辑
- [ ] **实现多模态 API 调用**：`multimodal_parser.py` 需要集成 DeepSeek-Vision 或 GPT-4V
- [ ] **结果验证规则完善**：confusion matrix 级别的质量评估

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

- [x] **【关键】安装并启动 Neo4j**（已完成）：Neo4j Community 5.26.25 @ `D:\Program Files\neo4j-community-5.26.25`
- [x] **【关键】配置 Neo4j 连接**（已完成）：`.env` 中 `bolt://localhost:7687`，密码 `chemsafe123`
- [x] **实现数据库索引创建**（已完成）：`schema_manager.py` 中的 `create_index_constraints()` 现会实际执行 Cypher
- [ ] **实现节点去重**：`batch_create_triples()` 需要检查节点是否存在再创建（已建 UNIQUE 约束，违反时会抛异常）
- [ ] **完善 ORM 模型**：`relational_db.py` 中的字段类型和约束需要根据实际数据调整
- [ ] **实现跨源链接**：`data_linker.py` 需要实现 Neo4j↔PostgreSQL 的数据联动

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

- [x] **实现因果路径检索**（已完成）：`CausalPathRetriever.retrieve()` 和 `find_causal_paths()` 均可实际执行 Cypher 查询
- [x] **实现上下文格式化**（已完成）：`format_context()` 将路径数据格式化为结构化的文本因果链
- [ ] **实现 jieba 分词集成**：`query_analyzer._extract_entities()` 需要用 jieba 分词 + 自定义化工词典
- [ ] **扩充意图关键词**：`INTENT_KEYWORDS` 需要根据更多查询场景扩充
- [ ] **实现模糊实体匹配**：`entity_linker.link_entities()` 需要实现精确→模糊→同义词三级匹配策略
- [ ] **完善 Cypher 模板**：`cypher_generator.py` 需要覆盖因果链、风险因素、缓解措施、统计等多种查询类型

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

- [x] **【关键】集成 LLM 调用**（已完成）：`answer_generator.generate()` 已验证可通过 DeepSeek API 生成回答
- [ ] **完善约束生成 Prompt**：`context_builder.GRAPH_RAG_SYSTEM_PROMPT` 需要细化约束规则
- [ ] **实现引用来源标注**：在生成答案时标注每条陈述对应的因果路径来源
- [ ] **实现上下文窗口管理**：当检索结果超过 LLM 上下文限制时进行截断或摘要
- [ ] **实现全文检索降级**：`fallback_handler.text_search_fallback()` 需要构建文本倒排索引
- [ ] **添加答案质量评估**：事实正确性自动校验（如检查生成的实体是否在 KG 中存在）

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

- [x] **实现问答界面交互**（已完成）：`app.py` 问答页面可实时连接 Neo4j，调用 QA 流水线生成回答
- [ ] **完善 KG 可视化**：`prepare_vis_data()` 的节点颜色、大小、标签需要优化
- [ ] **实现 Neo4j→vis 转换**：`convert_neo4j_to_vis()` 需要实际解析 Neo4j 路径对象
- [ ] **填充统计图表**：`stats_dashboard.py` 中的各图表方法需要实际数据
- [ ] **添加数据管理功能**：系统管理页面的数据流水线控制功能
- [ ] **UI/UX 优化**：布局、响应式、加载状态等

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

| 编号 | 待办项 | 涉及文件 | 预估工作量 |
|------|--------|---------|-----------|
| 1 | 填写 LLM API Key（DeepSeek / ChatGLM） | `.env` | ✅ 已完成 |
| 2 | 安装并启动 Neo4j 数据库 | 环境配置 | ✅ 已完成 (5.26.25) |
| 3 | 填写 Neo4j 连接信息 | `.env` | ✅ 已完成 |
| 4 | 测试 LLM API 连通性 | `src/extraction/llm_client.py` | ✅ 已完成 |
| 5 | 测试 Neo4j 连接 | `src/storage/neo4j_client.py` | ✅ 已完成 |
| 6 | 测试 Python 依赖安装 | `requirements.txt` | 30分钟 |

#### 🟡 P1 — 重要功能（核心业务逻辑）

| 编号 | 待办项 | 涉及文件 | 预估工作量 |
|------|--------|---------|-----------|
| 7 | 实现爬虫页面解析 | `src/acquisition/report_crawler.py` | ✅ 已完成（mem.gov.cn 94页，2000+事故） |
| 8 | 实现 PDF 文本提取 | `src/preprocessing/pdf_parser.py` | 1-2小时 |
| 9 | 实现 LLM 实体抽取 | `src/extraction/entity_extractor.py` | ✅ 已完成（样本验证通过） |
| 10 | 实现三元组→Neo4j写入 | `src/storage/neo4j_client.py` | ✅ 已完成（MERGE写入） |
| 11 | 实现 Cypher 查询生成 | `src/retrieval/cypher_generator.py` | 2小时 |
| 12 | 实现问答流水线串联 | `src/qa/answer_generator.py` | ✅ 已完成（Streamlit集成） |
| 13 | 实现前端问答交互 | `app.py` | ✅ 已完成（实时查询Neo4j） |

#### 🟢 P2 — 增强功能（提升质量和体验）

| 编号 | 待办项 | 涉及文件 | 预估工作量 |
|------|--------|---------|-----------|
| 14 | 扩充爬虫数据源 | `report_crawler.py` | ✅ 已完成（9个数据源） |
| 15 | 实现化学品物性 API | `src/acquisition/chemical_api.py` | ✅ 已完成（PubChem） |
| 16 | 实现气象数据获取 | `src/acquisition/weather_fetcher.py` | ✅ 已完成（Open-Meteo） |
| 17 | 实现扫描 PDF OCR | `src/preprocessing/pdf_parser.py` | 3-4小时 |
| 18 | 数据集 EDA 与可视化 | `src/visualization/stats_dashboard.py` | 2小时 |
| 19 | 知识图谱可视化（Web） | `src/visualization/kg_visualizer.py` | 2-3小时 |
| 20 | Prompt 模板迭代优化 | `src/extraction/prompt_templates.py` | 3-4小时 |

#### 🔵 P3 — 锦上添花（可选加分项）

| 编号 | 待办项 | 涉及文件 | 预估工作量 |
|------|--------|---------|-----------|
| 21 | 多模态 P&ID 图识别 | `src/extraction/multimodal_parser.py` | 4-5小时 |
| 22 | 全文检索降级方案 | `src/qa/fallback_handler.py` | 1-2小时 |
| 23 | 多源数据融合分析 | `src/preprocessing/data_merger.py` | 2-3小时 |
| 24 | Docker 部署配置 | `Dockerfile` | 1-2小时 |
| 25 | 单元测试编写 | `tests/` | 3-4小时 |
| 26 | 事故风险预测（ML） | 新增 `src/analysis/` | 4-6小时 |

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
|-----------|------|---------|
| DeepSeek API Key / deepseek-v4-flash | LLM 抽取 + 问答生成 | ✅ 已配置并验证 |
| Neo4j 5.26.25 | 图数据库 | ✅ 已安装运行，Schema 已初始化 |
| 端到端流水线 (`run_demo_pipeline.py`) | 样本数据抽取→存储→检索→问答 | ✅ 已验证通过 |
| Streamlit Web 问答页面 | 自然语言交互 | ✅ 可实时查询 Neo4j |
| 化学品物性 API (PubChem) | 物性数据获取 | ✅ 已实现（无需 Key） |
| 气象数据 API (Open-Meteo) | 天气数据获取 | ✅ 已实现（无需 Key） |
| 事故数据源 URL | 爬虫配置 | ✅ 已填入 8 个网址 |
| 爬虫页面解析逻辑 | HTML 列表提取 + PDF 下载 | ❌ 待实现 |
| 真实事故报告数据 | 构建完整 KG | ❌ 未采集 |
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
- ✅ **Streamlit 问答**：`app.py` 可实时查询 Neo4j 并生成回答
- ⏳ **PDF 解析**：`pdf_parser.py` 待集成 pdfplumber
- ❌ **其他数据源爬虫**：ciedu.com.cn(502)、ichemsafe.com(需登录) 待实现

### 7.2 关键风险

| 风险 | 影响 | 应对 |
|------|------|------|
| LLM API 调用费用 | 可能需要预算 | ✅ 已配置，控制调用量（先小批量测试） |
| Neo4j 环境配置 | 开发初期阻塞 | ✅ 已解决，5.26.25 已运行 |
| 爬虫数据源不可用 | 核心数据缺失 | mem.gov.cn 已解决，主数据源可用 |
| LLM 抽取质量低 | KG 质量不达标 | Prompt 迭代 + 人工抽样验证 |

### 7.3 推荐的开发顺序

1. **第9-10周（已完成）**：环境配置 ✅ | 数据源URL配置 ✅ | 爬虫实现 ✅
2. **第11周**：实现 PDF 解析 → 爬取更多数据 → EDA
3. **第12-13周（已完成）**：LLM 抽取流水线 ✅ | Neo4j 入库 ✅ | 批量抽取脚本 ✅
4. **第14周（已完成框架）**：Graph RAG 检索 ✅ | 问答生成 ✅ | 前端串联 ✅
5. **第15周**：爬虫采集真实数据 → 扩充 KG → 可视化优化 → 演示准备
6. **第16周**：报告撰写 → 代码整理 → 部署配置

---

*本文档会随项目进度持续更新。每次完成一个 TODO 项后，请在对应位置标记完成。*
