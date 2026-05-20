"""
PDF 事故报告解析模块

将扫描版/文字版 PDF 事故报告转换为可处理的纯文本。
支持 OCR 降级方案。

TODO [数据接入]: 需要根据报告的实际格式调整解析策略
"""
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF 报告解析器"""

    # TODO [完善]: 根据实际报告格式调整
    # - 部分报告可能为扫描图片PDF，需要OCR
    # - 不同来源的报告页眉页脚格式可能不同

    def parse(self, pdf_path: Path) -> Optional[str]:
        """
        解析 PDF 文件，提取纯文本内容。

        Args:
            pdf_path: PDF 文件路径

        Returns:
            提取的纯文本内容，失败返回 None
        """
        if not pdf_path.exists():
            logger.error(f"PDF 文件不存在: {pdf_path}")
            return None

        logger.info(f"开始解析 PDF: {pdf_path}")
        try:
            import pdfplumber
            text_pages = []
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    # 提取当前页文本
                    page_text = page.extract_text()
                    if page_text:
                        text_pages.append(page_text)
                    else:
                        logger.debug(f"第 {i+1} 页未提取到文本 (可能是扫描页或纯图片)")
            
            if not text_pages:
                logger.warning(f"未能从 {pdf_path} 提取到任何文本，可能全是扫描图片。")
                return None
                
            # 将各页文本合并，使用双换行符分隔段落
            full_text = "\n\n".join(text_pages)
            return self._clean_text(full_text)
            
        except ImportError:
            logger.error("未安装 pdfplumber，请运行 `pip install pdfplumber`")
            return None
        except Exception as e:
            logger.error(f"解析 PDF 失败 [{pdf_path}]: {e}")
            return None

    def _clean_text(self, raw_text: str) -> str:
        """文本清理：去除多余空白、页眉页脚等"""
        if not raw_text:
            return ""
            
        # 去除不可见字符 (如 \x00)
        text = raw_text.replace('\x00', '')
        
        # 简单的连续换行清理 (将3个以上的换行替换为2个)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 去除每行首尾的空白字符
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
