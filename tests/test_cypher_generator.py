import unittest

from src.retrieval.cypher_generator import CypherGenerator


class CypherGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.generator = CypherGenerator()

    def test_escapes_entity_name_in_causal_query(self):
        query = self.generator.generate(
            {
                "intent": "causal_chain",
                "entities": ["苯' }) MATCH (n) DETACH DELETE n //"],
            }
        )

        self.assertIn("苯\\' }) MATCH", query)
        self.assertIn("name:", query)

    def test_routes_mitigation_intent(self):
        query = self.generator.generate(
            {
                "intent": "mitigation",
                "entities": ["爆炸"],
            }
        )

        self.assertIn("mitigated_by", query)
        self.assertIn("爆炸", query)

    def test_clamps_statistics_limit(self):
        query = self.generator.generate(
            {
                "intent": "statistics",
                "constraints": {"group_by": "relation", "limit": 100000},
            }
        )

        self.assertIn("LIMIT 100", query)

    def test_fallback_escapes_contains_query(self):
        query = self.generator.generate({"intent": "unknown", "entities": ["氯气\\泄漏"]})

        self.assertIn("氯气\\\\泄漏", query)
        self.assertIn("CONTAINS", query)


if __name__ == "__main__":
    unittest.main()
