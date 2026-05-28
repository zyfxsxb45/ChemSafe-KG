"""
实体嵌入匹配模块

基于 sentence-transformers 的语义相似度匹配，补全纯词法匹配的盲区。
使"液氯"能匹配到"氯气"、"高温"能匹配到"温度升高"等。

用法:
    embedder = EntityEmbedder()
    embedder.load_or_build(entity_names)
    results = embedder.find_similar("液氯", top_k=3)

依赖: pip install sentence-transformers
降级: 未安装时 find_similar() 返回空列表，不影响原有匹配逻辑
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import os

# 从 .env 加载 HuggingFace 配置（SSL 绕过等）
from dotenv import load_dotenv
load_dotenv()
if os.getenv("HF_HUB_DISABLE_SSL_VERIFY"):
    os.environ.setdefault("HF_HUB_DISABLE_SSL_VERIFY", os.getenv("HF_HUB_DISABLE_SSL_VERIFY"))
if os.getenv("HF_ENDPOINT"):
    os.environ.setdefault("HF_ENDPOINT", os.getenv("HF_ENDPOINT"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    logger.warning("sentence-transformers 未安装，嵌入匹配不可用。pip install sentence-transformers")


class EntityEmbedder:
    """基于嵌入的实体语义匹配器"""

    # 轻量级多语言模型，支持中文，约 470MB
    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    CACHE_FILE = "data/processed/entity_embeddings.npz"

    def __init__(self):
        self.model: Optional["SentenceTransformer"] = None
        self.entity_names: List[str] = []
        self.embeddings: Optional[np.ndarray] = None
        self._loaded = False

    def load_or_build(self, entity_names: List[str], force_rebuild: bool = False):
        """
        加载缓存的嵌入，或重新计算并缓存。

        Args:
            entity_names: 全量实体名称列表
            force_rebuild: 强制重新计算（忽略缓存）
        """
        if not HAS_SENTENCE_TRANSFORMERS:
            return

        self.entity_names = entity_names

        if not force_rebuild:
            loaded = self._load_cache(entity_names)
            if loaded:
                return

        logger.info(f"计算 {len(entity_names)} 个实体的嵌入向量 (模型: {self.MODEL_NAME})...")
        self.model = SentenceTransformer(self.MODEL_NAME)
        self.embeddings = self.model.encode(
            entity_names,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        self._loaded = True

        self._save_cache()
        logger.info(f"嵌入计算完成，已缓存至 {self.CACHE_FILE}")

    def find_similar(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.45,
    ) -> List[Dict]:
        """
        查找与查询语义最相似的实体。

        Args:
            query: 用户问题或关键词
            top_k: 最多返回结果数
            threshold: 相似度阈值（低于此值的不返回）

        Returns:
            [{"name": "氯气", "score": 0.87}, ...]
            按相似度降序排列
        """
        if not self._loaded or self.embeddings is None:
            return []

        if self.model is None:
            self.model = SentenceTransformer(self.MODEL_NAME)

        query_emb = self.model.encode([query], normalize_embeddings=True)[0]

        # 余弦相似度 = 点积 (因已归一化)
        sims = np.dot(self.embeddings, query_emb)

        top_indices = np.argsort(sims)[-top_k:][::-1]
        results = []
        for idx in top_indices:
            score = float(sims[idx])
            if score >= threshold:
                results.append({
                    "name": self.entity_names[idx],
                    "score": round(score, 3),
                })
        return results

    # ─── 缓存读写 ────────────────────────────────────────────────────────

    def _cache_path(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent / self.CACHE_FILE

    def _load_cache(self, entity_names: List[str]) -> bool:
        """尝试加载缓存。实体列表必须完全一致才命中。"""
        cache_path = self._cache_path()
        if not cache_path.exists():
            return False
        try:
            data = np.load(cache_path, allow_pickle=True)
            cached_names = data.get("names")
            if cached_names is not None and list(cached_names) == entity_names:
                self.embeddings = data["embeddings"]
                self._loaded = True
                logger.info(f"加载嵌入缓存 ({len(entity_names)} 实体)")
                return True
            else:
                logger.info("实体列表已变更，重新计算嵌入")
                return False
        except Exception as e:
            logger.warning(f"嵌入缓存加载失败: {e}")
            return False

    def _save_cache(self):
        """保存嵌入缓存到本地文件。"""
        cache_path = self._cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            cache_path,
            names=self.entity_names,
            embeddings=self.embeddings,
        )
