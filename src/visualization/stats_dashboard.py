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
        )
        fig.update_traces(marker_color="#F44336")
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
        """事故类型分布饼图（基于预分类列）"""
        if df.empty:
            return self._empty_fig("暂无数据")

        if "accident_type" in df.columns:
            type_counts = df["accident_type"].value_counts()
        else:
            # 降级：关键词匹配
            from collections import Counter
            type_counter = Counter()
            for _, row in df.iterrows():
                txt = str(row.get("title","")) + " " + str(row.get("root_cause",""))
                for typ, keywords in TYPE_KEYWORDS.items():
                    if any(kw in txt for kw in keywords):
                        type_counter[typ] += 1; break
            type_counts = pd.Series(type_counter)

        fig = px.pie(
            names=type_counts.index, values=type_counts.values,
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

        # 准备数据
        df = chem_df.dropna(subset=available).copy()

        fig = px.scatter(
            df,
            x="flash_point",
            y="lower_explosion_limit",
            text="chemical_name",
            title="化学品安全风险矩阵（闪点越低越易燃，爆炸下限越低越危险）",
            labels={
                "flash_point": "闪点 (℃)",
                "lower_explosion_limit": "爆炸下限 (%)",
            },
            color="toxicity_class" if "toxicity_class" in df.columns else None,
            hover_data=["cas_number"],
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

        # 直接用预计算列
        if "accident_type" in sql_df.columns:
            type_counts = sql_df["accident_type"].value_counts()
            stats["top_type"] = type_counts.index[0] if len(type_counts) > 0 else "未知"
            stats["type_breakdown"] = dict(type_counts)
        else:
            stats["top_type"] = "未知"
            stats["type_breakdown"] = {}

        return stats

    # ── 天气-事故关联分析 ────────────────────────────────────────────────
    def weather_accident_correlation(self, accidents_df: pd.DataFrame,
                                      weather_df: pd.DataFrame) -> go.Figure | None:
        """天气温度与事故数量的关联散点图"""
        if accidents_df.empty or weather_df.empty:
            return None
        if "date" not in accidents_df.columns:
            return None

        df = accidents_df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["year_month"] = df["date"].dt.to_period("M")
        monthly = df.groupby("year_month").size().reset_index(name="accidents")
        monthly["year_month"] = monthly["year_month"].astype(str)

        wdf = weather_df.copy()
        if "date" in wdf.columns:
            wdf["date"] = pd.to_datetime(wdf["date"], errors="coerce")
            wdf["year_month"] = wdf["date"].dt.to_period("M").astype(str)

            merged = monthly.merge(wdf, on="year_month", how="inner")
            if merged.empty:
                return None

            fig = px.scatter(
                merged, x="temperature_max", y="accidents",
                hover_data=["year_month"],
                title=f"气温与事故数量关联（月度聚合，天气覆盖{len(merged)}个月）",
                labels={"temperature_max": "最高气温 (°C)", "accidents": "事故数"},
                color="temperature_max", color_continuous_scale="RdBu_r",
            )
            fig.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper",
                text=f"天气覆盖率约{len(merged)/len(monthly)*100:.0f}%，统计显著性有限",
                showarrow=False, font=dict(size=11, color="gray"), bgcolor="rgba(0,0,0,0.5)")
            fig.update_layout(height=400)
            return fig
        return None

    def weather_seasonality(self, accidents_df: pd.DataFrame) -> go.Figure:
        """事故月度分布（季节性分析）"""
        if accidents_df.empty or "date" not in accidents_df.columns:
            return self._empty_fig("暂无数据")

        df = accidents_df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["month"] = df["date"].dt.month
        monthly = df.groupby("month").size().reset_index(name="count")
        months_cn = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
        monthly["month_label"] = monthly["month"].apply(lambda x: months_cn[x-1] if 1<=x<=12 else "")

        fig = px.bar(
            monthly, x="month_label", y="count",
            title="事故月度分布（季节性模式）",
            labels={"month_label": "月份", "count": "事故数"},
            color="count", color_continuous_scale="Reds",
        )
        fig.update_layout(height=400, xaxis_title="月份", yaxis_title="事故数", showlegend=False)
        return fig

    # ── 化学品-事故关联分析 ──────────────────────────────────────────────
    def chemical_cooccurrence_heatmap(self, accidents_df: pd.DataFrame) -> go.Figure:
        """化学品共现热力图：哪些化学品常在同一起事故中出现"""
        if accidents_df.empty or "related_chemicals" not in accidents_df.columns:
            return self._empty_fig("暂无化学品数据")

        from collections import Counter
        import numpy as np

        # 提取每起事故的化学品列表
        chem_lists = []
        for val in accidents_df["related_chemicals"].dropna():
            chems = [c.strip() for c in str(val).split(",") if len(c.strip()) >= 2]
            if len(chems) >= 2:
                chem_lists.append(chems)

        if not chem_lists:
            return self._empty_fig("无多化学品事故")

        # 取 Top 15 化学品
        all_chems = Counter()
        for cl in chem_lists:
            all_chems.update(cl)
        top_chems = [c for c, _ in all_chems.most_common(15)]

        # 计算共现矩阵
        n = len(top_chems)
        matrix = np.zeros((n, n))
        chem_idx = {c: i for i, c in enumerate(top_chems)}
        for cl in chem_lists:
            relevant = [c for c in cl if c in chem_idx]
            for i, c1 in enumerate(relevant):
                for c2 in relevant[i+1:]:
                    matrix[chem_idx[c1]][chem_idx[c2]] += 1
                    matrix[chem_idx[c2]][chem_idx[c1]] += 1

        # 对称矩阵用上三角
        fig = go.Figure(data=go.Heatmap(
            z=matrix, x=top_chems, y=top_chems,
            colorscale="Blues", showscale=True,
            hovertemplate="%{x} + %{y}: %{z} 起<extra></extra>",
        ))
        fig.update_layout(
            title="化学品共现热力图（同一起事故中同时出现的频次）",
            height=500, xaxis_tickangle=45,
        )
        return fig

    def chemical_accident_type_cross(self, accidents_df: pd.DataFrame) -> go.Figure:
        """化学品 vs 事故类型交叉表"""
        if accidents_df.empty:
            return self._empty_fig("暂无数据")

        TYPE_KEYWORDS = {
            "爆炸": ["爆炸", "爆燃", "闪爆"], "中毒": ["中毒", "窒息"],
            "火灾": ["火灾", "起火"], "泄漏": ["泄漏", "泄露"],
        }

        from collections import Counter
        # 取 Top 10 化学品
        chem_counter = Counter()
        for val in accidents_df["related_chemicals"].dropna():
            for c in str(val).split(","):
                c = c.strip()
                if len(c) >= 2:
                    chem_counter[c] += 1
        top_chems = [c for c, _ in chem_counter.most_common(10)]

        # 交叉统计
        rows = []
        for _, acc in accidents_df.iterrows():
            txt = str(acc.get("title", "")) + " " + str(acc.get("root_cause", ""))
            atype = "其他"
            for t, kws in TYPE_KEYWORDS.items():
                if any(kw in txt for kw in kws):
                    atype = t; break
            chems_raw = str(acc.get("related_chemicals", ""))
            for chem in top_chems:
                if chem in chems_raw:
                    rows.append({"化学品": chem, "事故类型": atype})

        if not rows:
            return self._empty_fig("无交叉数据")

        cross_df = pd.DataFrame(rows)
        pivot = cross_df.groupby(["化学品", "事故类型"]).size().reset_index(name="count")

        fig = px.bar(
            pivot, x="化学品", y="count", color="事故类型",
            title="化学品 × 事故类型交叉分析",
            labels={"count": "事故数"},
            barmode="stack",
            color_discrete_sequence=["#F44336", "#FF9800", "#FF5722", "#2196F3"],
        )
        fig.update_layout(height=450, xaxis_tickangle=45)
        return fig

    # ── 数据洞察分析（图表+文字答案）─────────────────────────────────

    def insight_chem_risk_vs_freq(self, accidents_df: pd.DataFrame,
                                   chem_df: pd.DataFrame):
        """问题1: 最易燃易爆的化学品事故频率是否更高？"""
        if accidents_df.empty or chem_df.empty:
            return None, "数据不足"
        if "related_chemicals" not in accidents_df.columns:
            return None, "缺化学品关联数据"

        from collections import Counter
        chem_freq = Counter()
        for val in accidents_df["related_chemicals"].dropna():
            for c in str(val).split(","):
                c = c.strip()
                if len(c) >= 2: chem_freq[c] += 1

        # 取既有物性又有事故频次的化学品
        df = chem_df.dropna(subset=["flash_point", "lower_explosion_limit"]).copy()
        df["accident_count"] = df["chemical_name"].map(lambda x: chem_freq.get(x, 0))
        df = df[df["accident_count"] > 0]

        if len(df) < 5:
            return None, "样本不足"

        fig = px.scatter(
            df, x="flash_point", y="accident_count",
            text="chemical_name",
            title="闪点 vs 事故频次",
            labels={"flash_point": "闪点(℃)", "accident_count": "事故数"},
        )
        fig.update_traces(textposition="top center")
        fig.update_layout(height=400)

        # 分析
        low_fp = df[df["flash_point"] < 0]["accident_count"].mean()
        high_fp = df[df["flash_point"] >= 23]["accident_count"].mean()
        insight = (
            f"**发现**: 闪点<0℃的化学品平均 {low_fp:.1f} 起事故, "
            f"闪点≥23℃的平均 {high_fp:.1f} 起。"
        )
        if low_fp > high_fp:
            insight += "低闪点（更易燃）化学品确实事故更多。"
        else:
            insight += "未观察到显著正相关，事故频次受更多因素影响。"
        return fig, insight

    def insight_seasonal_pattern(self, accidents_df: pd.DataFrame):
        """问题2: 不同季节的事故类型分布有差异吗？"""
        if accidents_df.empty or "date" not in accidents_df.columns:
            return None, "缺日期数据"

        df = accidents_df.dropna(subset=["date"]).copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["month"] = df["date"].dt.month
        df["season"] = df["month"].map({12:"冬",1:"冬",2:"冬",3:"春",4:"春",5:"春",
                                         6:"夏",7:"夏",8:"夏",9:"秋",10:"秋",11:"秋"})

        TYPE_KW = {"爆炸":["爆炸","爆燃","闪爆"],"中毒":["中毒","窒息"],"火灾":["火灾","起火"]}
        rows = []
        for _, r in df.iterrows():
            txt = str(r.get("title","")) + str(r.get("root_cause",""))
            at = "其他"
            for t, kws in TYPE_KW.items():
                if any(kw in txt for kw in kws): at = t; break
            rows.append({"season": r["season"], "type": at})

        cross = pd.DataFrame(rows).groupby(["season","type"]).size().reset_index(name="count")

        fig = px.bar(cross, x="season", y="count", color="type", barmode="group",
                     title="不同季节的事故类型分布",
                     labels={"season":"季节","count":"事故数"},
                     color_discrete_sequence=["#F44336","#FF9800","#FF5722"],
                     category_orders={"season": ["春","夏","秋","冬"]})
        fig.update_layout(height=380)

        summer = cross[cross["season"]=="夏"]["count"].sum()
        winter = cross[cross["season"]=="冬"]["count"].sum()
        s_explosion = cross[(cross["season"]=="夏")&(cross["type"]=="爆炸")]["count"].sum()
        w_explosion = cross[(cross["season"]=="冬")&(cross["type"]=="爆炸")]["count"].sum()
        insight = (f"**发现**: 夏季共 {summer} 起, 冬季 {winter} 起。")
        if s_explosion > w_explosion:
            insight += f"夏季爆炸事故({s_explosion})多于冬季({w_explosion})，但数据无法区分温度因素与季节性生产活动差异。"
        return fig, insight

    def insight_equipment_chem_pair(self, accidents_df: pd.DataFrame):
        """问题3: 哪些设备-化学品组合事故最多？"""
        if accidents_df.empty:
            return None, "数据不足"

        from collections import Counter
        pairs = Counter()
        for _, r in accidents_df.iterrows():
            eqs = [e.strip() for e in str(r.get("related_equipment","")).split(",") if len(e.strip())>=2]
            chs = [c.strip() for c in str(r.get("related_chemicals","")).split(",") if len(c.strip())>=2]
            # 每起事故只取出现最多的1种设备×1种化学品 避免笛卡尔积虚高
            eq = eqs[0] if eqs else None
            ch = chs[0] if chs else None
            if eq and ch:
                pairs[f"{eq}+{ch}"] += 1

        top = pairs.most_common(12)
        if not top:
            return None, "无设备-化学品关联"

        df_pairs = pd.DataFrame(top, columns=["组合", "事故数"])
        fig = px.bar(df_pairs, x="事故数", y="组合", orientation="h",
                     title="最危险设备-化学品组合 Top 12",
                     color="事故数", color_continuous_scale="Reds")
        fig.update_layout(height=420, yaxis=dict(autorange="reversed"))

        insight = f"**发现**: '{top[0][0]}' 组合事故最多({top[0][1]}起)。"
        if len(top) >= 3:
            insight += f" 前3组合: {top[0][0]}, {top[1][0]}, {top[2][0]}。"
        return fig, insight

    def insight_year_trend(self, accidents_df: pd.DataFrame):
        """问题4: 事故频率是否在逐年下降？"""
        if accidents_df.empty or "date" not in accidents_df.columns:
            return None, "缺日期"

        df = accidents_df.dropna(subset=["date"]).copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["year"] = df["date"].dt.year
        yearly = df.groupby("year").size().reset_index(name="count")
        yearly = yearly[(yearly["year"]>=1990)&(yearly["year"]<=2025)]

        fig = px.line(yearly, x="year", y="count", markers=True,
                      title="事故年度趋势 (1990-2025)",
                      labels={"year":"年份","count":"事故数"})
        fig.update_layout(height=350)
        fig.update_traces(line_color="#F44336")

        before2015 = yearly[yearly["year"]<=2015]["count"].mean()
        after2015 = yearly[yearly["year"]>2015]["count"].mean()
        change = (after2015 - before2015) / before2015 * 100
        insight = (f"**发现**: 2015年前年均 {before2015:.0f} 起, 后年均 {after2015:.0f} 起, "
                   f"变化 {change:+.0f}%。")
        if change < -10:
            insight += "事故频率呈下降趋势，与2016年安全生产综合治理时间点吻合，但数据无法证明因果关系。"
        return fig, insight

    def insight_cause_pattern(self, accidents_df: pd.DataFrame):
        """问题5: 事故根因中违规操作占比多少？"""
        if accidents_df.empty:
            return None, "数据不足"

        CAUSE_PATTERNS = {
            "违规操作": ["违规", "违章", "擅自", "未办理", "未按", "未落实", "未佩戴", "未检测"],
            "设备故障": ["故障", "失效", "损坏", "腐蚀", "泄漏", "老化", "缺陷"],
            "管理缺失": ["管理", "制度", "培训", "审批", "整改", "隐患", "监督"],
            "设计缺陷": ["设计", "工艺", "选型"],
        }
        from collections import Counter
        cause_count = Counter()
        for _, r in accidents_df.iterrows():
            txt = str(r.get("root_cause","")) + str(r.get("title",""))
            matched = False
            for cause, kws in CAUSE_PATTERNS.items():
                if any(kw in txt for kw in kws):
                    cause_count[cause] += 1; matched = True; break
            if not matched: cause_count["其他"] += 1

        df_cause = pd.DataFrame(cause_count.most_common(), columns=["根因类型", "事故数"])
        fig = px.pie(df_cause, names="根因类型", values="事故数",
                     title="事故根因类型分布",
                     color_discrete_sequence=["#F44336","#FF9800","#2196F3","#9C27B0","#9E9E9E"])
        fig.update_layout(height=400)

        violation_pct = cause_count.get("违规操作",0) / sum(cause_count.values()) * 100
        insight = (f"**发现**: 违规操作占根因的 {violation_pct:.0f}%, "
                   f"是最主要的事故原因。注: 根因来自关键词匹配，'泄漏'等词在根因和后果文本中均出现，分类存在重叠。")
        return fig, insight

    def insight_chain_depth(self, neo4j_client):
        """问题6: 哪些设备的因果链最长（事故最复杂）？"""
        if neo4j_client.graph is None:
            return None, "Neo4j未连接"

        try:
            r = neo4j_client.graph.run("""
                MATCH path = (e:Equipment)-[:leads_to*1..4]->(c:Consequence)
                WITH e, max(length(path)) AS max_depth, count(DISTINCT c) AS conseq_count
                RETURN e.name AS name, max_depth, conseq_count
                ORDER BY max_depth DESC LIMIT 10
            """).data()
        except Exception:
            return None, "查询超时"

        if not r:
            return None, "无数据"

        df = pd.DataFrame(r, columns=["设备", "最大因果深度", "关联后果数"])
        fig = px.bar(df, x="设备", y="最大因果深度", color="关联后果数",
                     title="设备因果链深度 Top 10",
                     labels={"最大因果深度":"最大因果步数"},
                     color_continuous_scale="Reds")
        fig.update_layout(height=400, xaxis_tickangle=45)

        insight = (f"**发现**: '{df.iloc[0]["设备"]}' 因果链最深({df.iloc[0]["最大因果深度"]}步)，"
                   f"涉及该设备的事故链条最复杂，最需要重点防范。")
        return fig, insight

    def insight_monthly_type(self, accidents_df: pd.DataFrame):
        """问题7: 爆炸事故集中在哪些月份？"""
        if accidents_df.empty or "date" not in accidents_df.columns:
            return None, "缺日期"

        df = accidents_df.dropna(subset=["date"]).copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["month"] = df["date"].dt.month
        df["is_explosion"] = df["title"].str.contains("爆炸|爆燃|闪爆", na=False)

        monthly = df.groupby("month").agg(
            total=("is_explosion", "count"),
            explosion=("is_explosion", "sum")
        ).reset_index()
        monthly["explosion_rate"] = monthly["explosion"] / monthly["total"] * 100

        fig = px.line(monthly, x="month", y="explosion_rate", markers=True,
                      title="各月爆炸事故占比 (%)",
                      labels={"month":"月份","explosion_rate":"爆炸占比(%)"})
        fig.update_layout(height=350)
        fig.update_traces(line_color="#F44336")

        peak = monthly.loc[monthly["explosion_rate"].idxmax()]
        insight = (f"**发现**: {int(peak['month'])}月爆炸占比最高({peak['explosion_rate']:.1f}%)。")
        if peak["month"] in [6,7,8]:
            insight += " 夏季月份爆炸占比高于其他季节，但数据无法区分是温度因素还是夏季生产活动增加所致。"
        return fig, insight

    # ── 辅助 ───────────────────────────────────────────────────────────────
    def _empty_fig(self, msg: str) -> go.Figure:
        fig = go.Figure()
        fig.add_annotation(text=msg, x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="gray"))
        fig.update_layout(height=300, xaxis=dict(showgrid=False, zeroline=False, visible=False),
                         yaxis=dict(showgrid=False, zeroline=False, visible=False))
        return fig
