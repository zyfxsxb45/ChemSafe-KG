import unittest

from src.retrieval.entity_linker import EntityLinker
from src.retrieval.entity_normalizer import EntityNormalizer


class EntityNormalizerTest(unittest.TestCase):
    def setUp(self):
        self.normalizer = EntityNormalizer()

    def test_normalizes_common_aliases(self):
        self.assertEqual(self.normalizer.normalize("形成爆炸性混合气体"), "形成爆炸性混合物")
        self.assertEqual(self.normalizer.normalize("阀门故障"), "阀门失效")
        self.assertEqual(self.normalizer.normalize("气体泄露"), "气体泄漏")
        self.assertEqual(self.normalizer.normalize("压力过高"), "超压")

    def test_removes_low_information_affixes(self):
        self.assertEqual(self.normalizer.normalize("导致物料泄露事故"), "物料泄漏")
        self.assertEqual(self.normalizer.normalize("  发生爆燃。"), "爆炸燃烧")

    def test_equivalent_uses_normalized_form(self):
        self.assertTrue(self.normalizer.equivalent("泄露", "泄漏"))
        self.assertTrue(self.normalizer.equivalent("温度过高", "超温"))


class EntityLinkerNormalizationTest(unittest.TestCase):
    def test_match_one_uses_normalized_names(self):
        linker = EntityLinker()
        linker._all_entities = [
            {
                "name": "形成爆炸性混合物",
                "type": "Abnormal_Condition",
                "normalized": "形成爆炸性混合物",
            }
        ]

        matched = linker._match_one("形成爆炸性混合气体")

        self.assertTrue(matched["matched"])
        self.assertEqual(matched["name"], "形成爆炸性混合物")
        self.assertEqual(matched["match_type"], "normalized")


if __name__ == "__main__":
    unittest.main()
