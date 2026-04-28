"""
文本清洗与标准化模块

对爬取/解析后的原始文档进行清洗和标准化处理，
为 LLM 知识抽取做好准备。
"""
import re
import logging
from typing import List
import pandas as pd

logger = logging.getLogger(__name__)


class TextCleaner:
    """文本清洗器"""

    def clean_report_text(self, text: str) -> str:
        """
        对单篇事故报告文本进行清洗。

        TODO [完善]:
          1. 去除不可见字符和乱码
          2. 标准化标点符号 (全角→半角)
          3. 去除页眉页脚 (基于规则)
          4. 段落结构保留
          5. 敏感信息脱敏 (人员姓名 → [姓名])
        """
        if not text:
            return ""

        text = self._normalize_whitespace(text)
        text = self._normalize_punctuation(text)
        # text = self._remove_headers_footers(text)
        # text = self._redact_pii(text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _normalize_punctuation(self, text: str) -> str:
        """标准化标点符号"""
        # 全角英文字母 → 半角
        text = re.sub(r'[Ａ-Ｚａ-ｚ]', lambda m: chr(ord(m.group(0)) - 0xFEE0), text)
        # 全角数字 → 半角
        text = re.sub(r'[０-９]', lambda m: chr(ord(m.group(0)) - 0xFEE0), text)
        return text

    def split_into_chunks(self, text: str, max_chars: int = 3000) -> List[str]:
        """
        将长文本分割为适合 LLM 处理的片段。
        按段落边界切分，避免在句子中间截断。

        TODO [完善]:
          1. 智能分段 (按事故经过/原因/应急等章节)
          2. 窗口重叠策略 (保证因果链完整性)
        """
        paragraphs = text.split('\n\n')
        chunks, current = [], []
        current_len = 0

        for para in paragraphs:
            if current_len + len(para) > max_chars and current:
                chunks.append('\n\n'.join(current))
                current, current_len = [], 0
            current.append(para)
            current_len += len(para)

        if current:
            chunks.append('\n\n'.join(current))

        return chunks

    def build_report_index(self, metadata: pd.DataFrame) -> pd.DataFrame:
        """构建报告索引表，记录每份报告的元信息和处理状态"""
        # TODO: 实现索引表构建
        return metadata
