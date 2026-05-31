"""TTS / 阿里云 DashScope（百炼）配置读写（.env + 连通性测试）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from .config import repo_root
from .llm_settings import env_file_path, mask_api_key, write_env_updates

DASHSCOPE_ENV = "DASHSCOPE_API_KEY"
DASHSCOPE_ALT_ENV = "TTS_DASHSCOPE_API_KEY"


def dashscope_api_key() -> str:
    return (os.getenv(DASHSCOPE_ENV) or os.getenv(DASHSCOPE_ALT_ENV) or "").strip()


def tts_settings_public() -> dict[str, Any]:
    key = dashscope_api_key()
    return {
        "tts_provider": (os.getenv("TTS_PROVIDER") or "auto").strip(),
        "tts_fallback": (os.getenv("TTS_FALLBACK") or "dashscope,azure,openai").strip(),
        "dashscope_api_key_env": DASHSCOPE_ENV,
        "dashscope_api_key_set": bool(key),
        "dashscope_api_key_masked": mask_api_key(key),
        "env_path": str(env_file_path()),
        "help_url": "https://bailian.console.aliyun.com/",
    }


def save_tts_settings(
    *,
    dashscope_api_key: str | None = None,
    tts_provider: str | None = None,
    tts_fallback: str | None = None,
) -> dict[str, Any]:
    updates: dict[str, str] = {}
    if dashscope_api_key is not None and dashscope_api_key.strip() and "..." not in dashscope_api_key:
        updates[DASHSCOPE_ENV] = dashscope_api_key.strip()
    if tts_provider is not None and tts_provider.strip():
        updates["TTS_PROVIDER"] = tts_provider.strip()
    if tts_fallback is not None and tts_fallback.strip():
        updates["TTS_FALLBACK"] = tts_fallback.strip()

    env_path = None
    if updates:
        env_path = str(write_env_updates(updates))

    return {"saved": True, "env_path": env_path, "updated_keys": list(updates.keys())}


def _ensure_python_agent_path() -> None:
    root = str(repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def test_tts_connection(*, provider: str = "dashscope") -> dict[str, Any]:
    """探测 TTS；默认仅测 DashScope（需已配置 Key）。"""
    _ensure_python_agent_path()
    from python_agent.tts_provider import health_check

    key = dashscope_api_key()
    if provider == "dashscope" and not key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY，请在页面保存阿里云 Key 后重试")

    prev_provider = os.environ.get("TTS_PROVIDER")
    try:
        if provider == "dashscope":
            os.environ["TTS_PROVIDER"] = "dashscope"
        return health_check()
    finally:
        if prev_provider is None:
            os.environ.pop("TTS_PROVIDER", None)
        else:
            os.environ["TTS_PROVIDER"] = prev_provider
