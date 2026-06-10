"""
答案生成模块

在知识图谱因果路径的约束下，调用 LLM 生成最终回答。
"""
import logging
from typing import Dict, Optional, Callable, Generator
from src.extraction.llm_client import LLMClient
from src.qa.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """答案生成器"""

    def __init__(self):
        self.llm = LLMClient()
        self.context_builder = ContextBuilder()

    def generate(
        self,
        question: str,
        causal_context: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        基于因果上下文生成回答。

        Args:
            question: 用户问题
            causal_context: 检索到的因果路径文本

        Returns:
            LLM 生成的回答

        TODO [完善]:
          1. 答案的事实正确性校验
          2. 引用来源标注
          3. 不确定性表达 (当证据不足时)
        """
        if progress_callback:
            progress_callback("正在构建大模型提示词上下文...")
        system_prompt, user_prompt = self.context_builder.build(
            question, causal_context,
        )

        try:
            if progress_callback:
                progress_callback("正在调用大模型生成专业回答，请稍候...")
            answer = self.llm.chat(system_prompt, user_prompt)
            if progress_callback:
                progress_callback("回答生成完毕。")
            return answer
        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            return self._fallback_response(question, causal_context)

    def generate_stream(
        self,
        question: str,
        causal_context: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Generator[str, None, None]:
        """
        基于因果上下文流式生成回答 (Streaming)。
        """
        if progress_callback:
            progress_callback("正在构建大模型提示词上下文...")
        system_prompt, user_prompt = self.context_builder.build(
            question, causal_context,
        )

        if progress_callback:
            progress_callback("正在调用大模型流式生成专业回答...")
            
        try:
            for chunk in self.llm.chat_stream(system_prompt, user_prompt):
                yield chunk
            if progress_callback:
                progress_callback("回答生成完毕。")
        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            yield self._fallback_response(question, causal_context)

    def _fallback_response(self, question: str, context: str) -> str:
        """降级响应: 当 LLM 调用失败时返回检索到的原始信息"""
        return (
            f"⚠️ 大模型生成服务暂时不可用。\n\n"
            f"**检索到的相关因果信息**:\n{context}\n\n"
            f"**您的提问**: {question}"
        )
