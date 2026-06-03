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
        # 节点颜色 + 大小映射
        color_map = {
            "Equipment": "#4CAF50",
            "Material": "#2196F3",
            "Abnormal_Condition": "#FF9800",
            "Consequence": "#F44336",
            "Mitigation": "#9C27B0",
            "Accident": "#607D8B",
        }
        size_map = {
            "Consequence": 35,        # 事故后果最大
            "Equipment": 28,
            "Material": 25,
            "Abnormal_Condition": 22,
            "Mitigation": 20,
            "Accident": 30,
        }
        # 关系颜色映射
        edge_color_map = {
            "leads_to": "#FF5722",
            "involves": "#2196F3",
            "mitigated_by": "#4CAF50",
        }

        vis_nodes = []
        for node in nodes:
            group = node.get("group", "")
            vis_nodes.append({
                "id": node["id"],
                "label": node.get("label", node["id"]),
                "title": node.get("title", ""),
                "color": color_map.get(group, "#999"),
                "size": size_map.get(group, 20),
                "group": group,
            })

        vis_edges = []
        for edge in edges:
            rel_type = edge.get("label", "")
            vis_edges.append({
                "from": edge["from"],
                "to": edge["to"],
                "label": rel_type,
                "arrows": "to",
                "color": {"color": edge_color_map.get(rel_type, "#666")},
            })

        return {"nodes": vis_nodes, "edges": vis_edges}

    def convert_neo4j_to_vis(self, neo4j_paths: List) -> Dict:
        """
        将 Neo4j 查询路径结果转换为可视化数据。

        支持 CausalPathRetriever 返回的字典格式:
          {"node_names": ["A", "B"], "rel_types": ["leads_to"]}

        也兼容 py2neo Path 对象的 nodes / relationships 属性。
        """
        nodes, edges = [], []
        seen_nodes = set()
        seen_edges = set()

        def add_node(node_id, label=None, group=None, title=None):
            node_id = str(node_id)
            if node_id in seen_nodes:
                return
            seen_nodes.add(node_id)
            nodes.append({
                "id": node_id,
                "label": label or node_id,
                "group": group or "",
                "title": title or label or node_id,
            })

        for path in neo4j_paths or []:
            if isinstance(path, dict):
                node_names = path.get("node_names", [])
                rel_types = path.get("rel_types", [])
                for name in node_names:
                    add_node(name, label=name)
                for idx, rel_type in enumerate(rel_types):
                    if idx + 1 >= len(node_names):
                        continue
                    edge_id = f"{node_names[idx]}-{rel_type}-{node_names[idx + 1]}"
                    if edge_id in seen_edges:
                        continue
                    seen_edges.add(edge_id)
                    edges.append({
                        "from": str(node_names[idx]),
                        "to": str(node_names[idx + 1]),
                        "label": rel_type,
                    })
                continue

            path_nodes = getattr(path, "nodes", [])
            path_rels = getattr(path, "relationships", [])
            for node in path_nodes:
                node_id = getattr(node, "identity", None) or node.get("name")
                labels = list(getattr(node, "labels", []))
                add_node(
                    node_id,
                    label=node.get("name", str(node_id)),
                    group=labels[0] if labels else "",
                    title=node.get("name", str(node_id)),
                )
            for rel in path_rels:
                start_node = getattr(rel, "start_node", None)
                end_node = getattr(rel, "end_node", None)
                if start_node is None or end_node is None:
                    continue
                from_id = str(getattr(start_node, "identity", start_node.get("name")))
                to_id = str(getattr(end_node, "identity", end_node.get("name")))
                rel_label = type(rel).__name__
                edge_id = f"{from_id}-{rel_label}-{to_id}"
                if edge_id in seen_edges:
                    continue
                seen_edges.add(edge_id)
                edges.append({
                    "from": from_id,
                    "to": to_id,
                    "label": rel_label,
                })

        return self.prepare_vis_data(nodes, edges)
