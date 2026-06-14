import unittest

from src.visualization.kg_visualizer import KGFrontendVisualizer


class KGFrontendVisualizerTest(unittest.TestCase):
    def test_convert_dict_paths_preserves_node_types(self):
        visualizer = KGFrontendVisualizer()
        data = visualizer.convert_neo4j_to_vis(
            [
                {
                    "node_names": ["冷却水循环泵", "温度升高", "爆炸"],
                    "node_types": ["Equipment", "Abnormal_Condition", "Consequence"],
                    "rel_types": ["leads_to", "leads_to"],
                }
            ]
        )

        groups = {node["label"]: node["group"] for node in data["nodes"]}

        self.assertEqual(groups["冷却水循环泵"], "Equipment")
        self.assertEqual(groups["温度升高"], "Abnormal_Condition")
        self.assertEqual(groups["爆炸"], "Consequence")
        self.assertEqual(len(data["edges"]), 2)


if __name__ == "__main__":
    unittest.main()
