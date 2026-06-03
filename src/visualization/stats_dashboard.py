"""
统计分析仪表板模块

提供事故多维统计分析和交互式图表的可视化功能。
整合 Neo4j 和 SQLite 的多源数据，生成 Plotly 图表供 Streamlit 前端渲染。
"""
import logging
from typing import Optional, Dict, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

logger = logging.getLogger(__name__)

# 事故类型关键词映射
TYPE_KEYWORDS = {
    "爆炸": ["爆炸", "爆燃", "闪爆", "爆轰"],
    "中毒": ["中毒", "窒息"],
    "火灾": ["火灾", "起火", "燃烧"],
    "泄漏": ["泄漏", "泄露", "逸散"],
    "坍塌": ["坍塌", "倒塌"],
}


class StatsDashboard:
    """统计分析仪表板"""

    # ── 时间线分布 ────────────────────────────────────────────────────────
    def accident_timeline(self, df: pd.DataFrame) -> go.Figure:
        """事故时间序列分布图（按年份聚合）"""
        if df.empty or "date" not in df.columns:
            return self._empty_fig("暂无数据")

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["year"] = df["date"].dt.year.astype(str)
        df = df[df["year"] != "nan"]

        if df.empty:
            return self._empty_fig("暂无有效日期数据")

        trend = df.groupby("year").size().reset_index(name="count")

        fig = px.bar(
            trend,
            x="year",
            y="count",
            title="事故年份分布",
            labels={"year": "年份", "count": "事故数量"},
            color="count",
            color_continuous_scale="Reds",
        )
        fig.update_layout(
            xaxis_title="年份",
            yaxis_title="事故数量",
            showlegend=False,
            height=400,
        )
        return fig

    # ── 月度趋势（近期） ───────────────────────────────────────────────────
    def monthly_trend(self, df: pd.DataFrame, years: int = 5) -> go.Figure:
        """最近 N 年的事故月度趋势线"""
        if df.empty or "date" not in df.columns:
            return self._empty_fig("暂无数据")

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
        df = df[df["date"] >= cutoff]

        if df.empty:
            return self._empty_fig(f"近{years}年暂无数据")

        df["year_month"] = df["date"].dt.to_period("M").astype(str)
        trend = df.groupby("year_month").size().reset_index(name="count")

        fig = px.line(
            trend,
            x="year_month",
            y="count",
            title=f"近{years}年事故月度趋势",
            labels={"year_month": "月份", "count": "事故数量"},
            markers=True,
        )
        fig.update_layout(height=400)
        fig.update_traces(line_color="#FF5722")
        return fig

    # ── 事故类型分布 ───────────────────────────────────────────────────────
    def accident_type_pie(self, df: pd.DataFrame) -> go.Figure:
        """事故类型分布饼图（基于标题/描述关键词匹配）"""
        if df.empty:
            return self._empty_fig("暂无数据")

        type_counts = Counter()
        text_col = "title" if "title" in df.columns else "summary"
        for _, row in df.iterrows():
            txt = str(row.get(text_col, "")) + " " + str(row.get("root_cause", ""))
            matched = False
            for typ, keywords in TYPE_KEYWORDS.items():
                if any(kw in txt for kw in keywords):
                    type_counts[typ] += 1
                    matched = True
            if not matched:
                type_counts["其他"] += 1

        if not type_counts:
            return self._empty_fig("无法识别事故类型")

        fig = px.pie(
            names=list(type_counts.keys()),
            values=list(type_counts.values()),
            title="事故类型分布",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=400)
        return fig

    # ── 化学品频次统计 ────────────────────────────────────────────────────
    def chemical_frequency_bar(self, df: pd.DataFrame, top_n: int = 15) -> go.Figure:
        """事故中涉及的化学品频次统计"""
        if df.empty or "related_chemicals" not in df.columns:
            return self._empty_fig("暂无化学品数据")

        # 按逗号拆分 related_chemicals 并统计频次
        chem_counter = Counter()
        for val in df["related_chemicals"].dropna():
            for chem in str(val).split(","):
                chem = chem.strip()
                if chem and len(chem) >= 2:
                    chem_counter[chem] += 1

        if not chem_counter:
            return self._empty_fig("暂无化学品数据")

        top = chem_counter.most_common(top_n)
        fig = px.bar(
            x=[c for c, _ in top],
            y=[n for _, n in top],
            title=f"事故涉及化学品频次 (Top {top_n})",
            labels={"x": "化学品", "y": "出现次数"},
            color=[n for _, n in top],
            color_continuous_scale="Blues",
        )
        fig.update_layout(height=400, xaxis_tickangle=45)
        return fig

    # ── 设备故障频次统计 ───────────────────────────────────────────────────
    def equipment_frequency_bar(self, df: pd.DataFrame, top_n: int = 15) -> go.Figure:
        """事故中涉及的设备频次统计"""
        if df.empty or "related_equipment" not in df.columns:
            return self._empty_fig("暂无设备数据")

        eq_counter = Counter()
        for val in df["related_equipment"].dropna():
            for eq in str(val).split(","):
                eq = eq.strip()
                if eq and len(eq) >= 2:
                    eq_counter[eq] += 1

        if not eq_counter:
            return self._empty_fig("暂无设备数据")

        top = eq_counter.most_common(top_n)
        fig = px.bar(
            x=[e for e, _ in top],
            y=[n for _, n in top],
            title=f"事故涉及设备频次 (Top {top_n})",
            labels={"x": "设备", "y": "出现次数"},
            color=[n for _, n in top],
            color_continuous_scale="Greens",
        )
        fig.update_layout(height=400, xaxis_tickangle=45)
        return fig

    # ── 化学品风险矩阵 ────────────────────────────────────────────────────
    def chemical_risk_matrix(self, chem_df: pd.DataFrame) -> go.Figure:
        """化学品风险矩阵：闪点 vs 爆炸下限，气泡大小表示毒性"""
        if chem_df.empty:
            return self._empty_fig("暂无化学品物性数据")

        required_cols = ["chemical_name", "flash_point", "lower_explosion_limit"]
        available = [c for c in required_cols if c in chem_df.columns]
        if "chemical_name" not in available:
            return self._empty_fig("缺化学品名称数据")

        fig = px.scatter(
            chem_df.dropna(subset=available),
            x="flash_point",
            y="lower_explosion_limit",
            text="chemical_name",
            title="化学品风险矩阵",
            labels={
                "flash_point": "闪点 (℃)",
                "lower_explosion_limit": "爆炸下限 (%)",
            },
            size="vapor_pressure" if "vapor_pressure" in chem_df.columns else None,
            color="toxicity_class" if "toxicity_class" in chem_df.columns else None,
        )
        # 安全阈值线
        fig.add_hline(y=1.0, line_dash="dash", line_color="orange",
                       annotation_text="爆炸下限 1%")
        fig.add_vline(x=23, line_dash="dash", line_color="orange",
                      annotation_text="闪点 23℃")
        fig.update_traces(textposition="top center", marker=dict(size=12))
        fig.update_layout(height=500)
        return fig

    # ── Neo4j 图谱统计 ─────────────────────────────────────────────────────
    def neo4j_node_type_pie(self, neo4j_client) -> go.Figure:
        """Neo4j 节点类型分布（按 ChemSafe-KG 实体类型）"""
        try:
            data = neo4j_client.graph.run("""
                MATCH (n) WHERE size(labels(n)) > 0
                WITH labels(n)[0] AS label
                WHERE label IN ['Equipment','Material','Abnormal_Condition','Consequence','Mitigation','Accident']
                RETURN label, count(*) AS cnt
                ORDER BY cnt DESC
            """).data()
        except Exception as e:
            logger.warning(f"Neo4j 节点类型查询失败: {e}")
            return self._empty_fig("Neo4j 查询失败")

        if not data:
            return self._empty_fig("Neo4j 无数据")

        labels = [row["label"] for row in data]
        counts = [row["cnt"] for row in data]

        color_map = {
            "Equipment": "#4CAF50",
            "Material": "#2196F3",
            "Abnormal_Condition": "#FF9800",
            "Consequence": "#F44336",
            "Mitigation": "#9C27B0",
            "Accident": "#607D8B",
        }
        colors = [color_map.get(l, "#999") for l in labels]

        fig = px.pie(
            names=labels, values=counts,
            title="知识图谱节点类型分布",
            color=labels,
            color_discrete_map={l: color_map.get(l, "#999") for l in labels},
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=400)
        return fig

    # ── 因果链桑基图 ──────────────────────────────────────────────────────
    def causal_chain_sankey(self, neo4j_client, limit: int = 50) -> go.Figure:
        """因果链桑基图：展示从原因到后果的因果流"""
        try:
            data = neo4j_client.graph.run("""
                MATCH (a)-[r:leads_to]->(b)
                WHERE size(labels(a)) > 0 AND size(labels(b)) > 0
                WITH labels(a)[0] AS src_type, labels(b)[0] AS tgt_type,
                     count(*) AS weight
                WHERE src_type IN ['Equipment','Material','Abnormal_Condition','Consequence','Mitigation','Accident']
                  AND tgt_type IN ['Equipment','Material','Abnormal_Condition','Consequence','Mitigation','Accident']
                RETURN src_type, tgt_type, weight
                ORDER BY weight DESC
                LIMIT $limit
            """, limit=limit).data()
        except Exception as e:
            logger.warning(f"因果链查询失败: {e}")
            return self._empty_fig("因果链查询失败")

        if not data:
            return self._empty_fig("无因果关系边")

        # 构建桑基图
        all_types = sorted(set(
            [r["src_type"] for r in data] + [r["tgt_type"] for r in data]
        ))
        type_to_idx = {t: i for i, t in enumerate(all_types)}

        source = [type_to_idx[r["src_type"]] for r in data]
        target = [type_to_idx[r["tgt_type"]] for r in data]
        value = [r["weight"] for r in data]

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                label=all_types,
                color=["#4CAF50","#2196F3","#FF9800","#F44336","#9C27B0","#607D8B"],
                pad=15, thickness=20,
            ),
            link=dict(
                source=source, target=target, value=value,
                color=["rgba(255,152,0,0.3)" for _ in source],
            ),
        )])
        fig.update_layout(title="因果类型流转关系", height=400)
        return fig

    # ── 地区分布 ──────────────────────────────────────────────────────────
    def location_bar(self, df: pd.DataFrame, top_n: int = 10) -> go.Figure:
        """事故地区分布（按省份聚合）"""
        if df.empty or "location" not in df.columns:
            return self._empty_fig("暂无地区数据")

        loc_df = df.dropna(subset=["location"])
        if loc_df.empty:
            return self._empty_fig("暂无地区数据")

        # 从 location 字段提取省份（取前2-3个字）
        def extract_province(s: str) -> str:
            provinces = ["北京","天津","上海","重庆",
                        "河北","山西","辽宁","吉林","黑龙江",
                        "江苏","浙江","安徽","福建","江西","山东",
                        "河南","湖北","湖南","广东","广西","海南",
                        "四川","贵州","云南","西藏","陕西","甘肃","青海","宁夏","新疆",
                        "内蒙古"]
            for p in provinces:
                if str(s).startswith(p):
                    return p
            return str(s)[:3]

        loc_df = loc_df.copy()
        loc_df["province"] = loc_df["location"].apply(extract_province)
        province_counts = loc_df["province"].value_counts().head(top_n)

        fig = px.bar(
            x=province_counts.index,
            y=province_counts.values,
            title=f"事故地区分布 (Top {top_n})",
            labels={"x": "省份", "y": "事故数量"},
            color=province_counts.values,
            color_continuous_scale="OrRd",
        )
        fig.update_layout(height=400)
        return fig

    # ── 概要统计卡片 ──────────────────────────────────────────────────────
    def summary_stats(self, sql_df: pd.DataFrame, neo4j_client) -> dict:
        """生成概要统计数字"""
        stats = {}

        if not sql_df.empty and "date" in sql_df.columns:
            dates = pd.to_datetime(sql_df["date"], errors="coerce")
            stats["date_range"] = f"{dates.min().year}–{dates.max().year}" if len(dates.dropna()) > 0 else "未知"
        else:
            stats["date_range"] = "未知"

        stats["total_accidents"] = len(sql_df)

        try:
            stats["neo4j_nodes"] = neo4j_client.get_entity_count()
            stats["neo4j_rels"] = neo4j_client.get_relation_count()
        except Exception:
            stats["neo4j_nodes"] = 0
            stats["neo4j_rels"] = 0

        # 统计事故类型
        if not sql_df.empty:
            type_counter = Counter()
            text_col = "title" if "title" in sql_df.columns else "summary"
            for _, row in sql_df.iterrows():
                txt = str(row.get(text_col, "")) + " " + str(row.get("root_cause", ""))
                for typ, keywords in TYPE_KEYWORDS.items():
                    if any(kw in txt for kw in keywords):
                        type_counter[typ] += 1
                        break
            stats["top_type"] = type_counter.most_common(1)[0][0] if type_counter else "未知"
            stats["type_breakdown"] = dict(type_counter)
        else:
            stats["top_type"] = "未知"
            stats["type_breakdown"] = {}

        return stats

    # ── 辅助 ───────────────────────────────────────────────────────────────
    def _empty_fig(self, msg: str) -> go.Figure:
        fig = go.Figure()
        fig.add_annotation(text=msg, x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="gray"))
        fig.update_layout(height=300, xaxis=dict(showgrid=False, zeroline=False, visible=False),
                         yaxis=dict(showgrid=False, zeroline=False, visible=False))
        return fig
