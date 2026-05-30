"""Edge TTS 重试与错误分类。"""
from __future__ import annotations

import pytest

from python_agent.tts_edge import cache_key, is_retryable_error


def test_is_retryable_503_message() -> None:
    class E(Exception):
        pass

    exc = E("503, message='Invalid response status', url='wss://speech.platform.bing.com'")
    assert is_retryable_error(exc) is True


def test_is_retryable_not_generic() -> None:
    assert is_retryable_error(ValueError("bad text")) is False


def test_cache_key_stable() -> None:
    a = cache_key("你好", "zh-CN-YunxiNeural")
    b = cache_key("你好", "zh-CN-YunxiNeural")
    c = cache_key("你好", "zh-CN-XiaoxiaoNeural")
    assert a == b
    assert a != c
