"""
因果路径可视化模块

将知识图谱中检索到的因果路径以直观的有向图方式呈现。
支持单条路径和批量路径的可视化，使用 Plotly 渲染。
"""
import logging
from typing import List, Dict, Optional
import plotly.graph_objects as go
import networkx as nx

logger = logging.getLogger(__name__)

# 节点类型 → 颜色 / 符号
NODE_STYLE = {
    "Equipment":            {"color": "#4CAF50", "symbol": "square",        "size": 22},
    "Material":             {"color": "#2196F3", "symbol": "diamond",       "size": 20},
    "Abnormal_Condition":   {"color": "#FF9800", "symbol": "triangle-up",   "size": 24},
    "Consequence":          {"color": "#F44336", "symbol": "x",             "size": 26},
    "Mitigation":           {"color": "#9C27B0", "symbol": "star",          "size": 22},
    "Accident":             {"color": "#607D8B", "symbol": "circle",        "size": 20},
}
DEFAULT_STYLE = {"color": "#999", "symbol": "circle", "size": 18}

REL_STYLE = {
    "leads_to":     {"color": "#FF5722", "dash": "solid"},
    "involves":     {"color": "#2196F3", "dash": "dot"},
    "mitigated_by": {"color": "#4CAF50", "dash": "dash"},
}
DEFAULT_REL_STYLE = {"color": "#999", "dash": "solid"}


class CausalPathVisualizer:
    """因果路径可视化器"""

    def visualize_single_path(
        self,
        node_names: List[str],
        rel_types: List[str],
        node_type_map: Optional[Dict[str, str]] = None,
    ) -> go.Figure:
        """
        绘制单条因果路径的有向图。

        Args:
            node_names: ["冷却水循环泵", "温度升高", "爆炸"]
            rel_types:  ["leads_to", "leads_to"]
            node_type_map: {"冷却水循环泵": "Equipment", ...}

        Returns:
            Plotly Figure
        """
        if not node_names:
            return self._empty_fig("无因果路径")

        # 构建 NetworkX 有向图用于层次布局
        G = nx.DiGraph()
        for i, name in enumerate(node_names):
            ntype = (node_type_map or {}).get(name, "Abnormal_Condition")
            G.add_node(i, name=name, type=ntype)
        for i, rel in enumerate(rel_types):
            if i + 1 < len(node_names):
                G.add_edge(i, i + 1, relation=rel)

        # 使用层次布局
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
        except Exception:
            # 降级：线性布局
            pos = {i: (i * 2, 0) for i in range(len(node_names))}

        # 绘制边
        for u, v, data in G.edges(data=True):
            rel = data.get("relation", "leads_to")
            style = REL_STYLE.get(rel, DEFAULT_REL_STYLE)
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            fig = go.Figure() if "fig" not in dir() else fig
            # 边用 annotation 的箭头表示
            fig.add_annotation(
                x=x1, y=y1,
                ax=x0, ay=y0,
                xref="x", yref="y", axref="x", ayref="y",
                text=rel,
                showarrow=True,
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=2,
                arrowcolor=style["color"],
                font=dict(size=10, color=style["color"]),
                standoff=18,
                startstandoff=18,
            )

        # 收集 figure (如果 edge 为空需要初始化)
        try:
            fig
        except NameError:
            fig = go.Figure()

        # 绘制节点
        for i, name in enumerate(node_names):
            ntype = (node_type_map or {}).get(name, "Abnormal_Condition")
            style = NODE_STYLE.get(ntype, DEFAULT_STYLE)
            x, y = pos[i]

            fig.add_trace(go.Scatter(
                x=[x], y=[y],
                mode="markers+text",
                marker=dict(
                    size=style["size"],
                    color=style["color"],
                    symbol=style["symbol"],
                    line=dict(width=2, color="white"),
                ),
                text=[name],
                textposition="bottom center",
                textfont=dict(size=11),
                name=name,
                hovertemplate=f"<b>{name}</b><br>类型: {ntype}<extra></extra>",
                showlegend=False,
            ))

        fig.update_layout(
            title="因果路径图",
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False),
            height=350,
            margin=dict(l=40, r=40, t=50, b=40),
        )
        return fig

    def visualize_multiple_paths(
        self,
        paths: List[Dict],
        node_type_map: Optional[Dict[str, str]] = None,
        max_paths: int = 6,
    ) -> go.Figure:
        """
        绘制多条因果路径的对比图（水平排列）。

        Args:
            paths: [{"node_names": [...], "rel_types": [...]}, ...]
            node_type_map: 实体类型映射
            max_paths: 最多展示几条路径

        Returns:
            Plotly Figure (子图布局)
        """
        paths = paths[:max_paths]
        n_paths = len(paths)

        if n_paths == 0:
            return self._empty_fig("无因果路径")

        if n_paths == 1:
            p = paths[0]
            return self.visualize_single_path(
                p.get("node_names", []),
                p.get("rel_types", []),
                node_type_map,
            )

        # 多路径：使用子图
        cols = min(n_paths, 3)
        rows = (n_paths + cols - 1) // cols

        from plotly.subplots import make_subplots
        fig = make_subplots(
            rows=rows, cols=cols,
            subplot_titles=[f"路径 {i+1} (深度{len(p.get('node_names',[]))-1})" for i, p in enumerate(paths)],
            horizontal_spacing=0.12,
            vertical_spacing=0.2,
        )

        for idx, path_dict in enumerate(paths):
            row = idx // cols + 1
            col = idx % cols + 1
            node_names = path_dict.get("node_names", [])
            rel_types = path_dict.get("rel_types", [])

            if not node_names:
                continue

            # 线性布局（子图内不适用 graphviz）
            n = len(node_names)
            xs = list(range(n))
            ys = [0] * n

            for i, name in enumerate(node_names):
                ntype = (node_type_map or {}).get(name, "Abnormal_Condition")
                style = NODE_STYLE.get(ntype, DEFAULT_STYLE)
                fig.add_trace(
                    go.Scatter(
                        x=[xs[i]], y=[ys[i]],
                        mode="markers+text",
                        marker=dict(size=style["size"]*0.7, color=style["color"], symbol=style["symbol"],
                                   line=dict(width=1.5, color="white")),
                        text=[name], textposition="bottom center",
                        textfont=dict(size=9),
                        hovertemplate=f"<b>{name}</b><br>类型: {ntype}<extra></extra>",
                        showlegend=False,
                    ),
                    row=row, col=col,
                )

            for i, rel in enumerate(rel_types):
                if i + 1 >= n:
                    continue
                style = REL_STYLE.get(rel, DEFAULT_REL_STYLE)
                fig.add_annotation(
                    x=xs[i+1], y=ys[i+1],
                    ax=xs[i], ay=ys[i],
                    xref=f"x{idx+1}", yref=f"y{idx+1}",
                    axref=f"x{idx+1}", ayref=f"y{idx+1}",
                    text=rel, showarrow=True, arrowhead=2,
                    arrowcolor=style["color"],
                    font=dict(size=8, color=style["color"]),
                    standoff=12, startstandoff=12,
                )

            # 隐藏子图坐标轴
            fig.update_xaxes(
                showgrid=False, zeroline=False, visible=False,
                row=row, col=col,
            )
            fig.update_yaxes(
                showgrid=False, zeroline=False, visible=False,
                row=row, col=col,
            )

        fig.update_layout(
            title="多条因果路径对比",
            height=280 * rows,
            margin=dict(l=30, r=30, t=60, b=30),
        )
        return fig

    def visualize_from_neo4j_paths(
        self,
        neo4j_paths: List[Dict],
        top_k: int = 6,
    ) -> go.Figure:
        """
        从 Neo4j 因果路径查询结果直接生成可视化。

        Args:
            neo4j_paths: CausalPathRetriever.retrieve() 返回的结果列表
            top_k: 展示前 K 条路径

        Returns:
            Plotly Figure
        """
        # 收集所有路径中出现的实体类型（用于着色）
        node_type_map: Dict[str, str] = {}

        filtered = []
        for p in neo4j_paths:
            node_names = p.get("node_names", [])
            rel_types = p.get("rel_types", [])
            if len(node_names) >= 2:
                filtered.append({"node_names": node_names, "rel_types": rel_types})

        filtered.sort(key=lambda x: len(x["node_names"]), reverse=True)
        filtered = filtered[:top_k]

        return self.visualize_multiple_paths(filtered, node_type_map)

    # ── 图例说明 ──────────────────────────────────────────────────────────
    def render_legend(self) -> go.Figure:
        """渲染节点类型与关系类型的图例"""
        fig = go.Figure()

        # 节点类型图例
        for i, (ntype, style) in enumerate(NODE_STYLE.items()):
            fig.add_trace(go.Scatter(
                x=[i % 3], y=[-(i // 3)],
                mode="markers+text",
                marker=dict(size=style["size"]*0.8, color=style["color"], symbol=style["symbol"]),
                text=[ntype],
                textposition="middle right",
                textfont=dict(size=11),
                showlegend=False,
                hovertemplate=f"<b>{ntype}</b><extra></extra>",
            ))

        fig.update_layout(
            title="因果路径图例",
            height=180,
            xaxis=dict(showgrid=False, zeroline=False, visible=False, range=[-1, 4]),
            yaxis=dict(showgrid=False, zeroline=False, visible=False, range=[-3, 1]),
        )
        return fig

    def _empty_fig(self, msg: str) -> go.Figure:
        fig = go.Figure()
        fig.add_annotation(
            text=msg, x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(
            height=200,
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False),
        )
        return fig
