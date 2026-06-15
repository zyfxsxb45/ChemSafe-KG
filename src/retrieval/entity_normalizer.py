"""
实体名称规范化模块

用于降低 LLM 抽取和用户查询中的同义表达噪声。
当前实现为轻量规则，不依赖模型或图数据库，适合在抽取后处理、
实体链接和后续离线消歧脚本中复用。
"""
import re


class EntityNormalizer:
    """化工安全领域实体名称规范化器。"""

    EXACT_ALIASES = {
        "泄露": "泄漏",
        "物料泄露": "物料泄漏",
        "气体泄露": "气体泄漏",
        "阀门故障": "阀门失效",
        "阀故障": "阀门失效",
        "压力超标": "超压",
        "压力过高": "超压",
        "温度过高": "超温",
        "温度超标": "超温",
        "爆燃": "爆炸燃烧",
        "人员中毒死亡": "人员伤亡",
        "人员死亡": "人员伤亡",
        "人员受伤": "人员伤亡",
        "爆炸性混合气体": "爆炸性混合物",
        "形成爆炸性混合气体": "形成爆炸性混合物",
    }

    PHRASE_REPLACEMENTS = [
        ("泄露", "泄漏"),
        ("爆炸性混合气体", "爆炸性混合物"),
        ("爆炸性气体混合物", "爆炸性混合物"),
        ("可燃气体混合物", "可燃混合物"),
        ("压力超标", "超压"),
        ("压力过高", "超压"),
        ("温度过高", "超温"),
        ("温度超标", "超温"),
        ("阀门故障", "阀门失效"),
        ("阀故障", "阀门失效"),
    ]

    PREFIX_PATTERNS = [
        r"^(导致|造成|引发|发生|出现|产生)",
        r"^(由于|因|因其|由于其)",
    ]

    SUFFIX_PATTERNS = [
        r"(事故|事件|情况|现象)$",
    ]

    def normalize(self, name: str) -> str:
        """返回实体规范名，保留原有领域含义但去除常见表达差异。"""
        text = self._compact(name)
        if not text:
            return ""

        text = self.EXACT_ALIASES.get(text, text)
        for src, dst in self.PHRASE_REPLACEMENTS:
            text = text.replace(src, dst)

        for pattern in self.PREFIX_PATTERNS:
            text = re.sub(pattern, "", text)
        for pattern in self.SUFFIX_PATTERNS:
            text = re.sub(pattern, "", text)

        text = self._compact(text)
        return self.EXACT_ALIASES.get(text, text)

    def equivalent(self, left: str, right: str) -> bool:
        """判断两个实体名规范化后是否等价。"""
        return self.normalize(left) == self.normalize(right)

    def _compact(self, value: str) -> str:
        text = str(value or "").strip()
        text = re.sub(r"\s+", "", text)
        text = text.strip("，。；;:：、,. ")
        return text
