"""分镜 JSON 校验。"""
from __future__ import annotations

from python_agent.capabilities.plan_validate import validate_platform_copy, validate_platform_video_block


def _valid_block():
    return {
        "title": "测试标题",
        "body": "笔记正文" * 20,
        "effects": {"preset": "活力", "gradient": False},
        "clips": [
            {
                "start": 0,
                "end": 10,
                "hook_text": "钩子",
                "tts_text": "这是一段足够长的口播文案用于测试校验逻辑，需要累计超过四十个汉字才算通过最低门槛。",
                "transition_to_next": "slideup",
            },
            {
                "start": 12,
                "end": 22,
                "hook_text": "结尾",
                "tts_text": "第二段口播同样需要有足够字数，继续补充内容以满足校验器对总字数的最低要求。",
                "transition_to_next": "fade",
            },
        ],
    }


def test_validate_platform_block_ok() -> None:
    ok, msg = validate_platform_video_block("xhs", _valid_block(), broll_seconds=60)
    assert ok, msg


def test_validate_rejects_missing_preset() -> None:
    b = _valid_block()
    b["effects"] = {}
    ok, msg = validate_platform_video_block("douyin", b)
    assert not ok
    assert "preset" in msg


def test_validate_platform_copy() -> None:
    copy = {"douyin": _valid_block(), "xhs": _valid_block()}
    ok, msg = validate_platform_copy(copy, broll_seconds=60)
    assert ok, msg
