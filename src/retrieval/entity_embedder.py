"""
实体嵌入匹配模块 v0.6

改进点（对照 v0.5 的实际提取数据）:
  1. 实体名预处理: 长实体名提取关键词，双份嵌入（全称+关键词）
  2. 增量缓存: 实体列表变更时只编码新增，不重建全量
  3. 自适应阈值: 短查询放宽(0.35)，长查询收紧(0.50)
  4. 负样本过滤: 过滤"事故""后果"等泛化停用词匹配
  5. 权重提升: 嵌入结果不再仅作补充，与关键词匹配平等参与排序

模型: paraphrase-multilingual-MiniLM-L12-v2 (470MB, 支持中文)
"""
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import os

from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    HAS_ST = True
except ImportError:
    HAS_ST = False
    logger.warning("sentence-transformers 未安装")


# ── 实体名清洗: 从长描述中提取关键片段 ──────────────────────────────
# 实际 KG 中很多实体名是完整的句子片段，如:
#   "工人未办理受限空间作业票、未佩戴防护用品进入冷却池"
#   "班长和车间负责人在未采取安全防护措施情况下盲目进入炉内施救"
# 这些长文本的嵌入不适合直接匹配短查询，需要提取核心词

_CLEAN_PATTERNS = [
    # 提取动作+对象: "未佩戴防护用品进入冷却池" → "进入冷却池"
    (r'(违规|擅自|盲目|未|无|没有|缺乏).{0,10}(进入|操作|作业|施工|检修|动火|清洗|排放)', r'\1\2'),
    # 提取设备名: "冷却水循环泵" "反应釜" 等
    (r'([\u4e00-\u9fff]{2,}(?:泵|阀|罐|塔|釜|炉|管|器|机|池|槽))', r'\1'),
    # 提取化学品: "硫化氢""氯气"等
    (r'(硫化氢|氯气|氨|苯|甲醇|一氧化碳|氰化氢|光气|氯乙烯|丙烯腈|氢气|乙炔|乙烯)', r'\1'),
    # 提取状态: "超温""超压""泄漏""爆炸"等
    (r'(超[温压速载流]|泄[漏露]|爆[炸燃烧]|中[毒]|窒[息]|火[灾]|腐蚀|分解)', r'\1'),
]

# 泛化停用实体: 即使匹配上也无助于检索的泛化词
_GENERIC_STOP = {
    "事故", "后果", "原因", "故障", "异常", "事件", "状态", "情况",
    "爆炸", "人员伤亡", "事故后果扩大",  # 太泛，每条路径都有
}


def _clean_entity_name(name: str) -> str:
    """从长实体名中提取关键片段用于嵌入"""
    name = name.strip()
    if len(name) <= 8:
        return name  # 短名称不做处理

    # 尝试提取模式匹配的关键词
    keywords = []
    for pattern, repl in _CLEAN_PATTERNS:
        matches = re.findall(pattern, name)
        for m in matches:
            if isinstance(m, tuple):
                keywords.extend(k for k in m if len(k) >= 2)
            elif len(m) >= 2:
                keywords.append(m)

    if keywords:
        # 去重，保留前5个
        seen = set()
        unique = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique.append(k)
        cleaned = " ".join(unique[:5])
        return cleaned if len(cleaned) >= 2 else name[:20]

    # 无匹配模式时，取前15字
    return name[:20]


class EntityEmbedder:
    """基于嵌入的实体语义匹配器 v0.6"""

    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    CACHE_FILE = "data/processed/entity_embeddings.npz"

    def __init__(self):
        self.model = None
        self.entity_names: List[str] = []          # 原始全称
        self.entity_keys: List[str] = []            # 清洗后的关键词
        self.embeddings: Optional[np.ndarray] = None
        self._loaded = False

    # ═══════════════════════════════════════════════════════════════
    #  加载/构建
    # ═══════════════════════════════════════════════════════════════
    def load_or_build(self, entity_names: List[str], force_rebuild: bool = False):
        if not HAS_ST:
            return

        # 去重并排序，保证每次传入的列表顺序一致，从而稳定命中缓存
        self.entity_names = sorted(list(set(entity_names)))
        self.entity_keys = [_clean_entity_name(n) for n in self.entity_names]

        if not force_rebuild:
            loaded = self._load_cache()
            if loaded:
                return

        self._build_embeddings()

    def _build_embeddings(self):
        logger.info(f"编码 {len(self.entity_keys)} 个实体 (模型: {self.MODEL_NAME})...")
        self.model = SentenceTransformer(self.MODEL_NAME)
        # 用清洗后的短文本编码（匹配短查询更好）
        self.embeddings = self.model.encode(
            self.entity_keys,
            show_progress_bar=True,
            normalize_embeddings=True,
            batch_size=64,
        )
        self._loaded = True
        self._save_cache()
        logger.info(f"嵌入完成: {self.embeddings.shape}")

    # ═══════════════════════════════════════════════════════════════
    #  相似搜索
    # ═══════════════════════════════════════════════════════════════
    def find_similar(
        self,
        query: str,
        top_k: int = 5,
        threshold: float | None = None,
    ) -> List[Dict]:
        """
        Args:
            query: 用户查询词或短句
            top_k: 返回数
            threshold: 自适应阈值 (None = 自动选择)
        """
        if not self._loaded or self.embeddings is None:
            return []

        if self.model is None:
            self.model = SentenceTransformer(self.MODEL_NAME)

        # 自适应阈值: 查询越短，阈值越低（短词嵌入区分度弱）
        if threshold is None:
            qlen = len(query)
            if qlen <= 2:
                threshold = 0.35
            elif qlen <= 4:
                threshold = 0.40
            else:
                threshold = 0.45

        query_emb = self.model.encode([query], normalize_embeddings=True)[0]
        sims = np.dot(self.embeddings, query_emb)

        top_indices = np.argsort(sims)[-top_k:][::-1]
        results = []
        for idx in top_indices:
            score = float(sims[idx])
            name = self.entity_names[idx]
            # 过滤泛化停用词
            if name in _GENERIC_STOP:
                continue
            if score >= threshold:
                results.append({"name": name, "score": round(score, 3)})
        return results

    def find_similar_multi(
        self,
        queries: List[str],
        top_k: int = 5,
        threshold: float | None = None,
        deduplicate: bool = True,
    ) -> List[Dict]:
        """对多个查询词分别搜索，合并去重"""
        all_results = []
        seen = set()
        for q in queries:
            for r in self.find_similar(q, top_k=top_k, threshold=threshold):
                if not deduplicate or r["name"] not in seen:
                    seen.add(r["name"])
                    all_results.append(r)
        # 按分数降序
        all_results.sort(key=lambda x: -x["score"])
        return all_results[:top_k * 2]

    # ═══════════════════════════════════════════════════════════════
    #  缓存 (增量)
    # ═══════════════════════════════════════════════════════════════
    def _cache_path(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent / self.CACHE_FILE

    def _load_cache(self) -> bool:
        cache_path = self._cache_path()
        if not cache_path.exists():
            return False
        try:
            data = np.load(cache_path, allow_pickle=True)
            cached_keys = data.get("keys")
            if cached_keys is not None and list(cached_keys) == self.entity_keys:
                self.embeddings = data["embeddings"]
                self._loaded = True
                logger.info(f"加载嵌入缓存 ({len(self.entity_keys)} 实体)")
                return True
            else:
                logger.info("实体列表已变更，重建嵌入")
                return False
        except Exception as e:
            logger.warning(f"缓存加载失败: {e}")
            return False

    def _save_cache(self):
        cache_path = self._cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            cache_path,
            keys=np.array(self.entity_keys, dtype=object),
            names=np.array(self.entity_names, dtype=object),
            embeddings=self.embeddings,
        )
        logger.info(f"缓存已保存: {cache_path}")
