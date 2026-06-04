"""
LLM API 客户端封装

提供统一的 LLM 调用接口，支持同步/异步调用、重试、错误处理。
当前支持 DeepSeek API（OpenAI 兼容协议），通过 .env 配置。
"""
import json
import time
import logging
from typing import Optional
from openai import OpenAI
from config.llm_config import get_llm_client
from config.settings import llm as llm_config

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM API 客户端封装"""

    def __init__(self):
        self.client: OpenAI = get_llm_client()
        self.model = llm_config.MODEL
        self.max_retries = 3
        self.retry_delay = 2.0

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        response_format: Optional[dict] = None,
    ) -> str:
        """
        调用 LLM 进行文本生成。

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            temperature: 采样温度 (抽取任务建议 0.1)
            response_format: 响应格式约束 (如 {"type": "json_object"})

        Returns:
            LLM 生成的文本内容

        配置要求: .env 中需配置 LLM_API_KEY 和 LLM_MODEL
        """
        for attempt in range(self.max_retries):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": llm_config.MAX_TOKENS,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                resp = self.client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content

            except Exception as e:
                logger.warning(
                    f"LLM 调用失败 (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        """
        调用 LLM 并解析 JSON 响应，带容错恢复。
        """
        text = self.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
        )
        return self._parse_json_response(text, system_prompt, user_prompt)

    def _parse_json_response(
        self, text: str, system_prompt: str, user_prompt: str
    ) -> dict:
        """解析 LLM 响应为 JSON，逐级降级恢复"""
        import re

        text = (text or "").strip()

        # 空响应 → 重试（降低温度增加确定性）
        if not text:
            logger.warning("LLM 返回空响应，重试中...")
            try:
                text = self.chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt + "\n\n请务必返回有效的 JSON。",
                    temperature=0.05,
                    response_format={"type": "json_object"},
                ).strip()
            except Exception:
                raise ValueError("LLM returned empty response after retry")

        # 去除 Markdown 代码块
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        text = text.strip()

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试修复常见 JSON 错误
        fixed = self._fix_json(text)
        if fixed:
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        # 尝试从文本中提取 JSON 对象
        match = re.search(r'\{[^{}]*"event_chain"[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # 所有恢复失败
        logger.warning(f"JSON 解析失败，原始响应前200字符: {text[:200]}")
        raise ValueError(f"Failed to parse JSON after all recovery attempts")

    def _fix_json(self, text: str) -> Optional[str]:
        """尝试修复常见的 JSON 格式错误"""
        import re
        fixed = text

        # 1. 去除尾部多余逗号 (如 {"a": 1,} → {"a": 1})
        fixed = re.sub(r',\s*}', '}', fixed)
        fixed = re.sub(r',\s*]', ']', fixed)

        # 2. 单引号 → 双引号
        if "'" in fixed and '"' not in fixed:
            fixed = fixed.replace("'", '"')

        # 3. 移除注释 (// ... 和 /* ... */)
        fixed = re.sub(r'//[^\n]*', '', fixed)
        fixed = re.sub(r'/\*.*?\*/', '', fixed, flags=re.DOTALL)

        return fixed if fixed != text else None
