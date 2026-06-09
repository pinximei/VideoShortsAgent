"""发布后验收模块单元测试。"""
from __future__ import annotations

from publisher.verify.pack import normalize_needle
from publisher.verify.scripts.registry import VERIFY_SCRIPTS, get_verify_script


def test_normalize_needle_strips_space() -> None:
    assert normalize_needle("让每场对话成为 AI 上下文？") == "让每场对话成为AI上下文？"[:18]


def test_verify_registry_four_channels() -> None:
    assert set(VERIFY_SCRIPTS.keys()) == {"douyin", "xhs", "toutiao", "douban"}
    s = get_verify_script("xhs")
    assert "find_title_in_list" in s.fixed_steps
