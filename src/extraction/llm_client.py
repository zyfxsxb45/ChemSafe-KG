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
        调用 LLM 并解析 JSON 响应。
        专为结构化知识抽取设计。
        """
        # TODO [完善]: 某些API可能不支持 response_format
        # 此时需要手动解析返回文本中的 JSON
        text = self.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
        )
        return json.loads(text)
