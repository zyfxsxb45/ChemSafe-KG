import unittest

from src.extraction.entity_extractor import EntityExtractor


class EntityExtractorTriplesTest(unittest.TestCase):
    def setUp(self):
        self.extractor = EntityExtractor.__new__(EntityExtractor)

    def test_convert_to_triples_supports_entity_then_relation_shape(self):
        result = {
            "event_chain": [
                {"entity": "冷却水循环泵", "type": "Equipment"},
                {"relation": "leads_to", "target": "温度升高"},
                {"entity": "温度升高", "type": "Abnormal_Condition"},
            ]
        }

        triples = self.extractor.convert_to_triples(result)

        self.assertEqual(triples, [("冷却水循环泵", "leads_to", "温度升高")])

    def test_convert_to_triples_supports_explicit_source_shape(self):
        result = {
            "event_chain": [
                {"source": "阀门失效", "relation": "leads_to", "target": "泄漏"},
                {"subject": "泄漏", "relation": "leads_to", "object": "火灾"},
            ]
        }

        triples = self.extractor.convert_to_triples(result)

        self.assertEqual(
            triples,
            [
                ("阀门失效", "leads_to", "泄漏"),
                ("泄漏", "leads_to", "火灾"),
            ],
        )

    def test_convert_to_triples_filters_invalid_edges(self):
        result = {
            "event_chain": [
                {"entity": "泄漏", "type": "Abnormal_Condition"},
                {"relation": "unknown", "target": "火灾"},
                {"relation": "leads_to", "target": "泄漏"},
                {"relation": "leads_to", "target": ""},
                {"relation": "leads_to", "target": "火灾"},
                {"relation": "leads_to", "target": "火灾"},
            ]
        }

        triples = self.extractor.convert_to_triples(result)

        self.assertEqual(triples, [("泄漏", "leads_to", "火灾")])


if __name__ == "__main__":
    unittest.main()
