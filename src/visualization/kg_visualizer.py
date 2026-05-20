"""
知识图谱可视化模块

使用 pyvis / streamlit-agraph 在 Web 端渲染知识图谱。
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class KGFrontendVisualizer:
    """知识图谱前端可视化器"""

    def prepare_vis_data(self, nodes: List[Dict], edges: List[Dict]) -> Dict:
        """
        将图数据转换为前端可视化所需的格式。

        Args:
            nodes: [{"id": "...", "label": "...", "group": "Equipment|..."}, ...]
            edges: [{"from": "...", "to": "...", "label": "leads_to"}, ...]

        Returns:
            可供 vis.js / streamlit-agraph 渲染的数据

        TODO [完善]:
          1. 节点颜色按类型区分
          2. 节点大小按度中心性调整
          3. 关系标签显示优化
          4. 布局算法选择 (层次布局适合因果图)
        """
        # 节点颜色映射
        color_map = {
            "Equipment": "#4CAF50",
            "Material": "#2196F3",
            "Abnormal_Condition": "#FF9800",
            "Consequence": "#F44336",
            "Mitigation": "#9C27B0",
        }

        vis_nodes = []
        for node in nodes:
            vis_nodes.append({
                "id": node["id"],
                "label": node.get("label", node["id"]),
                "title": node.get("title", ""),
                "color": color_map.get(node.get("group", ""), "#999"),
                "group": node.get("group", ""),
            })

        vis_edges = []
        for edge in edges:
            vis_edges.append({
                "from": edge["from"],
                "to": edge["to"],
                "label": edge.get("label", ""),
                "arrows": "to",
                "color": {"color": "#666"},
            })

        return {"nodes": vis_nodes, "edges": vis_edges}

    def convert_neo4j_to_vis(self, neo4j_paths: List) -> Dict:
        """
        将 Neo4j 查询路径结果转换为可视化数据。
        """
        nodes, edges = [], []
        seen_nodes = set()
        seen_edges = set()

        for path_dict in neo4j_paths:
            # 解析 CausalPathRetriever 返回的字典格式
            node_names = path_dict.get("node_names", [])
            rel_types = path_dict.get("rel_types", [])
            
            for i, name in enumerate(node_names):
                if name not in seen_nodes:
                    nodes.append({
                        "id": name,
                        "label": name,
                        "group": "Unknown"  # 默认分组，后续可扩展查询带上真实 Label
                    })
                    seen_nodes.add(name)
                    
                if i < len(rel_types):
                    source = name
                    target = node_names[i+1]
                    rel = rel_types[i]
                    edge_id = f"{source}-{rel}-{target}"
                    
                    if edge_id not in seen_edges:
                        edges.append({
                            "from": source,
                            "to": target,
                            "label": rel
                        })
                        seen_edges.add(edge_id)

        return self.prepare_vis_data(nodes, edges)
