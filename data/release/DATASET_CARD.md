# ChemSafe-KG 化工安全事故知识图谱数据集

> **版本**: v0.7.1 | **日期**: 2026-06-14 | **许可**: CC BY-NC 4.0（学术研究）

## 数据集概述

首个大规模结构化中文化工安全事故知识图谱数据集。覆盖 1,174 起事故（去重后）的因果链条，从应急管理部（mem.gov.cn）全量月度汇编和微信公众号事故分析文章中，通过 LLM 驱动的 Prompt Chain 策略自动抽取构建。配套 Neo4j 图数据库 6,976 节点、23,111 条因果关系边。

> ⚠ **数据覆盖说明**：本数据集代表的是被公开记录和报道的事故，不等同于全部化工安全事故总体。小型事故、未上报的未遂事件、因敏感原因未公开披露的重大事故均不在此数据集内。使用时需考虑这一覆盖偏差。

## v0.7.1 变更（相对 v0.7）

- 事故去重：通过标题相似度（>95%）识别并去除 405 条重复记录
- 数据集规模：1,579 → 1,174 条事故（去重 26%）
- 所有统计洞察和图表已基于去重后数据重新生成
- 定性结论不变，绝对数字更精确

## 文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| accidents.csv | 1,174 | 去重后事故主表（含 LLM 抽取根因、后果、类型、地点） |
| chemical_properties.csv | 72 | 危化品物性（PubChem：闪点/爆炸极限/毒性） |
| causal_triples.csv | 10,236 | 因果关系三元组（Neo4j 导出） |
| weather_records.csv | 108 | 历史天气记录（Open-Meteo，匹配事故地点日期） |

## accidents.csv 字段

| 字段 | 完整率 | 说明 |
|------|--------|------|
| title | 100% | 事故标题 |
| date | 72% | 事故日期（YYYY-MM-DD） |
| summary | 100% | 事故摘要（≤500字） |
| root_cause | 100% | LLM 抽取的根原因 |
| consequence | 100% | LLM 抽取的后果总结 |
| accident_type | 100% | 预分类标签：爆炸/中毒窒息/火灾/泄漏/坍塌/其他 |
| related_chemicals | 76% | 涉及的化学品名（逗号分隔） |
| related_equipment | 87% | 涉及的设备名（逗号分隔） |
| location | 55% | 提取的地理位置（省/市） |
| source_url | 100% | 数据来源标识（mem 简报/微信文章标题） |

## causal_triples.csv 字段

| 字段 | 说明 |
|------|------|
| src_type | Equipment / Material / Abnormal_Condition / Consequence / Mitigation |
| src | 源实体名称 |
| rel | leads_to / involves / mitigated_by |
| tgt_type | 目标实体类型 |
| tgt | 目标实体名称 |

## chemical_properties.csv 字段

| 字段 | 说明 |
|------|------|
| chemical_name | 化学品中文名称 |
| cas_number | CAS 号 |
| iupac_name | IUPAC 标准名 |
| molecular_weight | 分子量 |
| flash_point | 闪点（℃） |
| lower_explosion_limit | 爆炸下限（%） |
| toxicity_class | 毒性分类 |

## weather_records.csv 字段

| 字段 | 说明 |
|------|------|
| location | 省份/城市 |
| date | 事故日期（YYYY-MM-DD） |
| temperature_max | 最高温度（℃） |
| temperature_min | 最低温度（℃） |
| humidity | 湿度（%） |
| wind_speed | 风速（km/h） |
| precipitation | 降水量（mm） |
| weather_condition | 天气状况描述 |

## 构建方法

- **事故采集**: mem.gov.cn 全量月度汇编（1,261 份）+ 微信公众号（74 篇），BeautifulSoup 解析
- **知识抽取**: DeepSeek deepseek-v4-flash，Prompt Chain（5 实体 × 3 关系 + Few-shot + 8 条规则），200 线程并发，成功率 99%+
- **图存储**: Neo4j 5.26.25 Community，6,976 节点 / 23,111 关系
- **化学品**: PubChem API，72 种危化品安全物性
- **天气**: Open-Meteo Archive API，108 条事故地点与日期匹配记录

## 使用限制

1. 数据源为月度汇编简报（平均 150 字），非完整调查报告，因果链深度有限（1-2 跳为主）
2. LLM 抽取存在一定误差，因果链中个别节点可能偏离原文表述
3. 数据仅代表被公开记录的事故，不等同于全部化工安全事故总体
4. 2020 年代事故数量下降可能同时反映了安全改善和数据收录标准变化，使用时需交叉验证
5. 天气覆盖率 13%，天气-事故相关性分析仅能展示趋势，不具备统计显著性
6. 仅限学术研究和教育教学使用
7. 数据集持续更新中，当前版本可能非最终版

## 引用

```bibtex
@dataset{chemsafe-kg-v0.7.1-2026,
  title={ChemSafe-KG v0.7.1: A Large-Scale Knowledge Graph Dataset
         for Chemical Accident Causal Analysis},
  author={Zhai, Yifan and Yu, Liangyang and Zhao, Leyi},
  year={2026},
  version={0.7.1},
  note={CC BY-NC 4.0, academic use only.
        Dataset contains 1,174 deduplicated accident records,
        6,976 KG nodes, and 23,111 causal relations.}
}
```

## 致谢

本项目为清华大学《数据库技术及应用》课程项目（2026 年春季学期）。感谢王健楠教授的指导。

---

**数据集仓库**：https://github.com/zyfxsxb45/ChemSafe-KG  
**Release 下载**：https://github.com/zyfxsxb45/ChemSafe-KG/releases/tag/v0.7.1
