import unittest

from src.preprocessing.text_cleaner import TextCleaner


class TextCleanerTest(unittest.TestCase):
    def setUp(self):
        self.cleaner = TextCleaner()

    def test_clean_report_text_normalizes_and_redacts(self):
        raw = (
            "第 1 页 共 3 页\r\n"
            "ＡＢＣ１２３  发生泄漏\n\n\n"
            "联系人 13800138000，身份证 11010519491231002X"
        )

        cleaned = self.cleaner.clean_report_text(raw)

        self.assertIn("ABC123", cleaned)
        self.assertIn("[手机号]", cleaned)
        self.assertIn("[身份证号]", cleaned)
        self.assertNotIn("第 1 页 共 3 页", cleaned)
        self.assertNotIn("\n\n\n", cleaned)

    def test_split_into_chunks_keeps_paragraph_boundaries(self):
        text = "第一段事故经过\n\n第二段原因分析\n\n第三段处置措施"

        chunks = self.cleaner.split_into_chunks(text, max_chars=12)

        self.assertEqual(chunks, ["第一段事故经过", "第二段原因分析", "第三段处置措施"])


if __name__ == "__main__":
    unittest.main()
