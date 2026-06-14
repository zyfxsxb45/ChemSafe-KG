import unittest

from src.qa.context_builder import ContextBuilder


class ContextBuilderTest(unittest.TestCase):
    def setUp(self):
        self.builder = ContextBuilder()

    def test_build_counts_paths(self):
        _, user_prompt = self.builder.build(
            "为什么会爆炸？",
            "【路径 1】\nA\n【路径 2】\nB",
        )

        self.assertIn("共 2 条路径", user_prompt)

    def test_truncates_context_on_path_boundary(self):
        context = "导语\n" + "【路径 1】\n" + "A" * 20 + "\n【路径 2】\n" + "B" * 200

        truncated = self.builder._truncate_context(context, max_chars=40)

        self.assertIn("【路径 1】", truncated)
        self.assertNotIn("【路径 2】", truncated)
        self.assertIn("上下文已截断", truncated)


if __name__ == "__main__":
    unittest.main()
