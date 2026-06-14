import unittest

from src.extraction.llm_client import LLMClient


class LLMClientJsonParsingTest(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient.__new__(LLMClient)

    def test_parse_json_response_with_wrapping_text(self):
        text = """
        下面是抽取结果：
        {
          "event_chain": [
            {"entity": "阀门", "type": "Equipment"},
            {"relation": "leads_to", "target": "泄漏"},
            {"entity": "泄漏", "type": "Abnormal_Condition"}
          ],
          "root_cause": "阀门失效",
          "consequence": "泄漏"
        }
        如需更多信息请继续提问。
        """

        parsed = self.client._parse_json_response(text, "system", "user")

        self.assertEqual(parsed["root_cause"], "阀门失效")
        self.assertEqual(len(parsed["event_chain"]), 3)

    def test_extract_json_object_respects_braces_inside_strings(self):
        text = (
            'prefix {"event_chain": [{"entity": "反应釜{A}", "type": "Equipment"}], '
            '"root_cause": "异常", "consequence": "泄漏"} suffix'
        )

        extracted = self.client._extract_json_object(text)

        self.assertIn('"反应釜{A}"', extracted)
        self.assertTrue(extracted.startswith("{"))
        self.assertTrue(extracted.endswith("}"))

    def test_fix_json_removes_trailing_commas(self):
        fixed = self.client._fix_json('{"event_chain": [], "root_cause": "A",}')

        self.assertEqual(fixed, '{"event_chain": [], "root_cause": "A"}')


if __name__ == "__main__":
    unittest.main()
