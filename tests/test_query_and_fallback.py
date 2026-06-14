import unittest

from src.qa.fallback_handler import FallbackHandler
from src.retrieval.query_analyzer import QueryAnalyzer


class QueryAnalyzerTest(unittest.TestCase):
    def test_detects_mitigation_intent(self):
        result = QueryAnalyzer().analyze("硫化氢中毒事故有哪些应急措施？")

        self.assertEqual(result["intent"], "mitigation")
        self.assertEqual(result["original_question"], "硫化氢中毒事故有哪些应急措施？")


class FallbackHandlerTest(unittest.TestCase):
    def test_text_search_fallback_returns_matching_reports(self):
        text_index = {
            "r1": "苯泄漏后遇到点火源引发火灾。",
            "r2": "设备定期检修记录。",
        }

        result = FallbackHandler().text_search_fallback("苯 泄漏", text_index)

        self.assertIn("r1", result)
        self.assertIn("全文检索结果", result)

    def test_text_search_fallback_handles_no_match(self):
        result = FallbackHandler().text_search_fallback("氯气 泄漏", {"r1": "设备检修"})

        self.assertEqual(result, "未找到相关信息。")


if __name__ == "__main__":
    unittest.main()
