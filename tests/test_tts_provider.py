"""TTS 多渠道路由与 Key 后端。"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from python_agent.tts_key import available_key_providers, resolve_dashscope_voice
from python_agent.tts_provider import fallback_order, resolve_provider_chain, tts_provider_mode


def test_resolve_dashscope_voice_mapping() -> None:
    assert resolve_dashscope_voice("zh-CN-XiaoxiaoNeural") == "Cherry"
    assert resolve_dashscope_voice("zh-CN-YunxiNeural") == "Ethan"


def test_resolve_chain_edge_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "edge")
    assert resolve_provider_chain() == ["edge"]


def test_fallback_order_filters_missing_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("TTS_FALLBACK", "dashscope,azure,openai")
    assert fallback_order() == []


@patch("python_agent.tts_key.httpx.Client")
def test_dashscope_http_save_mp3(mock_client_cls: MagicMock, tmp_path: Path) -> None:
    from python_agent.tts_key import synthesize_dashscope

    post_resp = MagicMock()
    post_resp.status_code = 200
    post_resp.json.return_value = {
        "output": {"audio": {"url": "https://example.com/a.mp3"}},
    }
    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.content = b"\xff\xfb\x90" + b"\x00" * 800
    get_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = post_resp
    mock_client.get.return_value = get_resp
    mock_client_cls.return_value = mock_client

    out = tmp_path / "out.mp3"
    with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test"}):
        synthesize_dashscope("你好世界", "zh-CN-YunxiNeural", out)
    assert out.is_file()
    assert out.stat().st_size > 80
