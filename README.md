# ChemSafe-KG

> **LLM 驱动的化工安全事故知识图谱构建与因果推理问答系统**  
> 数据库技术及应用课程项目 · 清华大学化工系  
> **v0.7.1** · 1,174 起事故 · 6,976 节点 · 23,111 关系 · 图谱外实体 5.95→0.65  
> [📦 数据集下载](https://github.com/zyfxsxb45/ChemSafe-KG/releases/tag/v0.7.1)

---

## 一句话说清楚

用 DeepSeek 从 1,300+ 份中文化工事故报告中自动抽取因果链，建成知识图谱。然后检验这种方法能否提升化工安全问答的可控性。结论：约束机制有效（图谱外实体 5.95→0.65/题），但在简报式数据（平均 150 字）上，图谱规模的负面影响超过了约束的收益。统计分析反而更直接、更可靠。

---

## 数据规模

| 指标 | 数值 |
|------|------|
| 知识图谱节点 | **6,976**（Abnormal 3,570 / Accident 1,579 / Equipment 688 / Consequence 641 / Material 427 / Mitigation 71） |
| 因果关系边 | **23,111**（leads_to / involves / mitigated_by） |
| 事故记录（去重后） | **1,174**（SQLite，100% 含根因与后果，72% 含日期，100% 含预分类标签） |
| 化学品物性 | **72** 种（闪点 26 种 / 爆炸极限 31 种 / 毒性分类 43 种） |
| 天气记录 | **108** 条（Open-Meteo 历史天气，匹配事故地点与日期） |
| 地理位置 | **643** 条（从事故标题提取省/市，55% 覆盖） |
| 时间跨度 | 1947–2026 |

---

## 核心实验

**三组对照，同模型，唯一变量是检索方式。**

20 道题 × 7 种因果模式 × 3 组 baseline × 4 维评估。

| 指标 | 关键词 RAG | Graph RAG | 纯 LLM |
|------|-----------|-----------|--------|
| 图内约束率 | 40% | **70%** | 5% |
| 来源可追溯率 | 100% | 55% | 0% |
| 诚实拒答率 | 10% | **55%** | 0% |
| 平均图谱外实体数 | 1.2 | **0.65** | 5.95 |

> Graph RAG 将图谱外实体从 5.95 降至 0.65。纯 LLM 引用的实体可能来自训练数据，但无法区分来源。

---

## 系统架构

```
┌─ Streamlit Web 应用 ──────────────────────────────────────┐
│  问答 · 6维数据分析 · 交互式图谱 · 因果路径探索              │
├─ Graph RAG 检索 ─────────────────────────────────────────┤
│  三层实体匹配(精确/关键词/嵌入语义) → Cypher因果路径 → 约束生成  │
├─ 双存储 ────────────────────────────────────────────────┤
│  Neo4j 5.26.25(因果链图) + SQLite(结构化记录 + 统计分析)       │
├─ LLM 知识抽取 ──────────────────────────────────────────┤
│  DeepSeek v4-flash · Prompt Chain(8条规则) · JSON 3级容错  │
├─ 数据获取 ───────────────────────────────────────────────┤
│  mem.gov.cn(1,261份) · 微信公众号(74篇) · PubChem(72种) · Open-Meteo(108条) │
└─────────────────────────────────────────────────────────┘
```

---

## 快速开始

```bash
# 1. 安装
pip install -r requirements.txt

# 2. 配置
cp .env.example .env        # 填入 LLM_API_KEY 和 NEO4J_PASSWORD

# 3. 启动 Web 应用（需要 Neo4j 运行中 + 数据库已构建）
streamlit run app.py
```

**从头构建数据集**（需要 LLM API key + Neo4j 运行中）：

```bash
python scripts/rebuild_all.py    # 全量重建：爬虫 → 抽取 → 充实 → 验证
```

**运行对照实验**（需要 Neo4j 运行中 + 图谱已构建）：

```bash
python scripts/run_comparative_experiment_v2.py
```

**下载预构建数据集**（无需任何外部依赖，直接使用 CSV）：

→ [GitHub Releases v0.7.1](https://github.com/zyfxsxb45/ChemSafe-KG/releases/tag/v0.7.1)

> 注意：完整运行需要 DeepSeek API key + Neo4j 5.x + 约 1 小时构建时间。SQLite 数据库文件不在仓库中（需通过 rebuild_all.py 构建或从 Release 下载 CSV）。仅查看数据分析和统计洞察可通过 Release CSV 进行，无需 Neo4j。

---

## 项目结构

```
ChemSafe-KG/
├── app.py                              # Streamlit 应用（5 页面 + 6 标签页分析）
├── pipeline.py                         # CLI 流程编排
├── config/                             # 全局配置（数据库 + LLM + API）
├── src/
│   ├── acquisition/                    # 爬虫 + PubChem + Open-Meteo
│   ├── preprocessing/                  # 文本清洗 + 多源融合
│   ├── extraction/                     # LLM 抽取引擎（Prompt Chain + 容错）
│   ├── storage/                        # Neo4j + SQLite + DataLinker + Schema
│   ├── retrieval/                      # 因果路径检索 + 三层匹配 + 嵌入语义
│   ├── qa/                             # Graph RAG 约束生成
│   └── visualization/                  # 10+ 图表 + 图谱可视化 + 数据洞察
├── scripts/
│   ├── rebuild_all.py                  # ★ 全量重建（6 步自动化）
│   ├── run_comparative_experiment_v2.py # 三组对照实验
│   ├── classify_types.py               # 事故类型预分类
│   ├── enrich_chemicals.py             # 化学品物性扩充
│   ├── enrich_weather.py               # 天气数据匹配
│   ├── seed_chemicals.py               # PubChem 查询
│   ├── seed_safety.py                  # 安全物性填充
│   ├── dedup_accidents.py              # 事故去重（405条重复）
│   ├── explore_graph.py                # 图谱探索分析
│   ├── release_dataset.py              # 数据集导出
│   └── verify_rebuild.py               # 重建后验证
├── data/
│   ├── raw/                            # 原始采集数据
│   ├── processed/                      # SQLite 数据库 + 实验报告
│   └── release/                        # 公开数据集 CSV
└── docs/
    ├── framework-guide.md              # 五层架构详解
    └── kg_exploration.md               # 图谱探索报告
```

---

## 关键设计决策

**为什么双存储？** Neo4j 做因果链（"A 导致 B"天然有向边，变长路径查询一行 Cypher）。SQLite 做统计分析（COUNT + GROUP BY 比 Cypher 简洁）。不是过度设计——两种数据库解决的问题类型确实不同。

**为什么不用 LangChain？** 通用框架不能适配我们的 Prompt Chain（8 条专用规则 + 5 实体 × 3 关系 + Few-shot 示例）。自己实现给的控制粒度更大。

**为什么 temperature 设为 0.5？** 0.1 产生大量空响应（模型太 "确定"，JSON 长输出卡住）。0.7 输出不稳定。0.5 是空响应率 <1% 和抽取一致性之间的平衡点。

**为什么 max_tokens 是 16384？** 4096 截断 JSON 数组，8192 偶发截断。复杂事故多实体多关系需要完整输出。代价是 token 消耗增加，但 200 线程并发下成本可控。

---

## 已知局限

1. **数据天花板**。月度汇编平均 150 字，因果链深不过 3 层。不是算法瓶颈，是源材料的信息上限。
2. **天气覆盖率 13%**。108 条天气 vs 842 条有日期事故。只能看趋势，做不出统计显著推断。
3. **事故去重**。已通过标题相似度>95%识别并去除 405 条重复（26%），去重后 1,174 条。但缺少内容级去重（日期+地点+化学品组合匹配或标题嵌入相似度），仍有改进空间。
4. **图谱可视化受框架限制**。streamlit-agraph 不允许自定义 barnesHut 物理参数。
5. **测试覆盖率为零**。Prompt 迭代全靠手动跑例子，没有回归测试。

## 知识图谱如何才能真正有用

我们的实验证明了约束机制有效（图谱外实体 5.95→0.65），但整体效果受限于数据质量。几个明确可以激活 KG 价值的方向：

- **替换数据源**：CSB 调查报告每份数万字，含完整因果链和 safety recommendations。KG 可以自然映射为多层次因果图，支持跨事故的模式挖掘。
- **实体消歧**：合并同义节点（"形成爆炸性混合气体"="形成爆炸性混合物"），显著减少检索噪声，使跨事故因果链能够正确连接。
- **专用小图**：按事故类型或化学品分类建图，而非混合大图。小图检索噪音低，因果链更聚焦。
- **跨事故关联**：KG 的真正优势不在单次 QA，而在发现"不同事故共享同一因果模式"。这需要实体消歧和 schema 对齐后才能发挥。

---

## 技术栈

| 组件 | 技术 |
|------|------|
| LLM | DeepSeek deepseek-v4-flash（OpenAI 协议） |
| 图数据库 | Neo4j 5.26.25 + py2neo |
| 关系数据库 | SQLite + SQLAlchemy |
| 前端 | Streamlit + Plotly + streamlit-agraph |
| 嵌入匹配 | sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2, 470MB) |
| 中文分词 | jieba |
| 爬虫 | requests + BeautifulSoup + lxml |
| 化学品 API | pubchempy（PubChem） |
| 气象 API | Open-Meteo Archive（免费, 1940 年起） |
| 并发 | ThreadPoolExecutor（200 线程） |

---

## 更多文档

- [框架说明](docs/framework-guide.md) — 五层架构详解
- [数据集卡片](data/release/DATASET_CARD.md) — 字段说明与使用限制
- [图谱探索报告](docs/kg_exploration.md) — KG 在化工安全领域的真正潜力与实现路线

---

## 成员

翟彝凡 · 余亮阳 · 赵乐毅  
指导老师：王健楠 教授  
清华大学化学工程系 · 2026
