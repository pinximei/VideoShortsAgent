"""
LLM 客户端工厂

统一的 LLM 客户端创建入口。从 Config 读取 provider 配置，
支持任何 OpenAI 兼容 API（DashScope、DeepSeek、Ollama 等）。
"""
from openai import OpenAI
from python_agent.config import get_config


def create_llm_client(api_key: str = None, base_url: str = None) -> OpenAI:
    """创建 LLM 客户端

    Args:
        api_key: 覆盖配置的 API Key（可选）
        base_url: 覆盖配置的 API 地址（可选）

    Returns:
        OpenAI 兼容客户端实例
    """
    cfg = get_config()
    return OpenAI(
        api_key=api_key or cfg.llm_api_key,
        base_url=base_url or cfg.llm_base_url,
        timeout=120,
    )
