"""
因果路径可视化模块

专注于将知识图谱中检索到的因果路径以直观的方式呈现。
"""
from typing import List, Dict
import plotly.graph_objects as go


class CausalPathVisualizer:
    """因果路径可视化器"""

    def visualize_path(self, path_nodes: List[Dict], path_edges: List[Dict]) -> go.Figure:
        """
        绘制单条因果路径的流程图。

        Args:
            path_nodes: [{"name": "...", "type": "...", "status": "..."}, ...]
            path_edges: [{"source": i, "target": j, "relation": "leads_to"}, ...]

        Returns:
            Plotly Figure (有向图 / 流程图)

        TODO [完善]:
          1. 层次布局: 从左到右的因果流
          2. 节点样式: 不同实体类型不同颜色
          3. 交互: 悬停显示详情
        """
        fig = go.Figure()

        # 节点位置 (简单线性布局)
        x_positions = list(range(len(path_nodes)))
        y_positions = [0] * len(path_nodes)

        # 添加节点
        fig.add_trace(go.Scatter(
            x=x_positions,
            y=y_positions,
            mode="markers+text",
            marker=dict(size=30),
            text=[n["name"] for n in path_nodes],
            textposition="bottom center",
        ))

        # 添加关系边
        for edge in path_edges:
            fig.add_annotation(
                x=x_positions[edge["target"]],
                y=y_positions[edge["target"]],
                ax=x_positions[edge["source"]],
                ay=y_positions[edge["source"]],
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True,
                arrowhead=2,
                text=edge.get("relation", ""),
            )

        fig.update_layout(
            title="因果路径图",
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False),
            height=300,
        )
        return fig
