# ChemSafe-KG 化工安全事故知识图谱数据集

> **版本**: v0.7 | **日期**: 2026-06-09 | **许可**: CC BY-NC 4.0（学术研究）

## 数据集概述

**首个大规模结构化中文化工安全事故知识图谱数据集。**

覆盖 1174 起事故的因果链条，从应急管理部（mem.gov.cn）全量月度汇编和微信公众号事故分析文章中，通过 LLM 驱动的 Prompt Chain 策略自动抽取构建。配套 Neo4j 图数据库 6,976 节点、23,111 条因果关系边。

## 文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| accidents.csv | 1,579 | 事故主表（含 LLM 抽取根因、后果、类型、地点） |
| chemical_properties.csv | 72 | 危化品物性（PubChem：闪点/爆炸极限/毒性） |
| causal_triples.csv | 14,099 | 因果关系三元组（Neo4j 导出，leads_to+involves+mitigated_by） |
| weather_records.csv | 108 | 历史天气记录（Open-Meteo，匹配事故地点日期） |

## accidents.csv 字段

| 字段 | 完整率 | 说明 |
|------|--------|------|
| title | 100% | 事故标题 |
| date | 79% | 事故日期（YYYY-MM-DD） |
| summary | 100% | 事故摘要（≤500字） |
| root_cause | 100% | LLM 抽取的根原因 |
| consequence | 100% | LLM 抽取的后果总结 |
| accident_type | 100% | 预分类标签：爆炸/中毒窒息/火灾/泄漏/坍塌/其他 |
| related_chemicals | ~39% | 涉及的化学品名（逗号分隔） |
| related_equipment | ~53% | 涉及的设备名（逗号分隔） |
| location | ~63% | 提取的地理位置（省/市） |
| source_url | 100% | 数据来源标识 |

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
| molecular_weight | 分子量 |
| flash_point | 闪点（℃） |
| lower_explosion_limit | 爆炸下限（%） |
| toxicity | 毒性分类 |

## weather_records.csv 字段

| 字段 | 说明 |
|------|------|
| location | 省份/城市 |
| accident_date | 关联事故日期 |
| temperature_max / temperature_min | 最高/最低温度（℃） |
| precipitation | 降水量（mm） |
| wind_speed_max | 最大风速（km/h） |

## 构建方法

- **事故采集**: mem.gov.cn 全量月度汇编（1,261 份）+ 微信公众号（74 篇），BeautifulSoup 解析
- **知识抽取**: DeepSeek deepseek-v4-flash，Prompt Chain（5 实体 × 3 关系 + Few-shot + 8 条规则），200 线程并发，成功率 99%+
- **图存储**: Neo4j 5.26.25 Community，6,976 节点 / 23,111 关系
- **化学品**: PubChem API，72 种危化品安全物性
- **天气**: Open-Meteo Archive API，998 条地点 × 108 条天气匹配

## 使用限制

1. 数据源为月度汇编简报，非完整调查报告，描述较简略（平均 150 字）
2. LLM 抽取存在一定误差，因果链中个别节点可能偏离原文
3. 仅限学术研究和教育教学使用
4. 数据集持续更新中，当前版本可能非最终版

## 引用

```
@dataset{chemsafe-kg-v0.7-2026,
  title={ChemSafe-KG v0.7: A Large-Scale Knowledge Graph Dataset for Chemical Accident Causal Analysis},
  author={Zhai, Yu, Zhao},
  year={2026},
  note={CC BY-NC 4.0, academic use only}
}
```

## 致谢

本项目为清华大学《数据库技术及应用》课程项目。感谢王健楠教授的指导。
