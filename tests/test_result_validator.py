import unittest

from src.extraction.result_validator import ResultValidator


class ResultValidatorTest(unittest.TestCase):
    def setUp(self):
        self.validator = ResultValidator()

    def test_accepts_valid_extraction_result(self):
        result = {
            "event_chain": [
                {"entity": "冷却水循环泵", "type": "Equipment"},
                {"relation": "leads_to", "target": "温度升高"},
                {"entity": "温度升高", "type": "Abnormal_Condition"},
                {"relation": "leads_to", "target": "爆炸"},
                {"entity": "爆炸", "type": "Consequence"},
            ],
            "root_cause": "冷却水循环泵故障",
            "consequence": "爆炸",
        }

        self.assertTrue(self.validator.validate_structure(result))
        self.assertEqual(self.validator.validate_entity_types(result), [])
        self.assertEqual(self.validator.validate_relation_types(result), [])
        self.assertEqual(self.validator.calculate_confidence(result), 1.0)

    def test_rejects_empty_or_incomplete_chain(self):
        result = {
            "event_chain": [{"entity": "冷却水循环泵", "type": "Equipment"}],
            "root_cause": "冷却水循环泵故障",
            "consequence": "爆炸",
        }

        self.assertFalse(self.validator.validate_structure(result))
        self.assertLess(self.validator.calculate_confidence(result), 1.0)

    def test_reports_invalid_entity_and_relation_types(self):
        result = {
            "event_chain": [
                {"entity": "冷却水循环泵", "type": "Machine"},
                {"relation": "makes", "target": "温度升高"},
            ],
            "root_cause": "冷却水循环泵故障",
            "consequence": "温度升高",
        }

        self.assertFalse(self.validator.validate_structure(result))
        self.assertEqual(self.validator.validate_entity_types(result), ["Machine"])
        self.assertEqual(self.validator.validate_relation_types(result), ["makes"])

    def test_normalizes_common_aliases_without_mutating_input(self):
        result = {
            "event_chain": [
                {"entity": "阀门", "type": "equipment"},
                {"relation": "cause", "target": "泄漏"},
                {"entity": "泄漏", "type": "Abnormal"},
            ],
            "root_cause": "阀门失效",
            "consequence": "泄漏",
        }

        normalized = self.validator.normalize_result(result)

        self.assertEqual(normalized["event_chain"][0]["type"], "Equipment")
        self.assertEqual(normalized["event_chain"][1]["relation"], "leads_to")
        self.assertEqual(normalized["event_chain"][2]["type"], "Abnormal_Condition")
        self.assertEqual(result["event_chain"][0]["type"], "equipment")

    def test_does_not_normalize_reverse_causality(self):
        result = {
            "event_chain": [
                {"entity": "泄漏", "type": "Abnormal_Condition"},
                {"relation": "caused_by", "target": "阀门失效"},
            ],
            "root_cause": "阀门失效",
            "consequence": "泄漏",
        }

        self.assertEqual(self.validator.validate_relation_types(result), ["caused_by"])
        self.assertFalse(self.validator.validate_structure(result))


if __name__ == "__main__":
    unittest.main()
