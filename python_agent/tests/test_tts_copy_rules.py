from python_agent.eval_mock_compose import mock_compose_from_brief
from python_agent.tts_copy_rules import (
    sanitize_tts_text,
    tts_has_banned_phrase,
    tts_has_meta_filler,
    validate_slides_tts_copy,
)


def test_mock_compose_no_banned_phrases():
    script = mock_compose_from_brief({"feed_kind": "github_daily", "stars": "9k"})
    assert not validate_slides_tts_copy(script["slides"])


def test_banned_detected():
    assert tts_has_banned_phrase("这是第2个重点，建议收藏")


def test_meta_filler_stripped():
    raw = "能生成桌面工具。开源 MIT，个人学习和小团队都能用。"
    out = sanitize_tts_text(raw)
    assert "MIT" not in out
    assert "生成" in out


def test_mock_compose_product_focus():
    script = mock_compose_from_brief(
        {
            "feed_kind": "github_daily",
            "talking_points": ["用自然语言生成小工具", "本机处理隐私资料", "适合日报汇总"],
        }
    )
    joined = " ".join(str(s.get("tts_text") or "") for s in script["slides"])
    assert not tts_has_meta_filler(joined)
    assert "协议" not in joined
