"""
LLM API 客户端配置

基于 OpenAI SDK 封装，兼容 DeepSeek / ChatGLM / OpenAI 等 API。
"""
from openai import OpenAI
from config.settings import llm as llm_config


def create_llm_client() -> OpenAI:
    """创建 LLM API 客户端实例"""
    return OpenAI(
        api_key=llm_config.API_KEY,
        base_url=llm_config.BASE_URL,
    )


# 全局单例客户端
_default_client: OpenAI | None = None


def get_llm_client() -> OpenAI:
    """获取 LLM 客户端单例"""
    global _default_client
    if _default_client is None:
        _default_client = create_llm_client()
    return _default_client
