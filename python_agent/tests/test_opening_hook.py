from python_agent.capabilities.opening_hook import (
    enforce_opening_hook_on_copy,
    scroll_stopping_hook,
)


def test_scroll_stopping_hook_question() -> None:
    h = scroll_stopping_hook(title="Bluedot 2.1：Apple Watch录音", hook="")
    assert "？" in h or "?" in h
    assert len(h) <= 28


def test_enforce_first_clip_opening() -> None:
    copy = {
        "douyin": {
            "title": "长标题",
            "effects": {"preset": "严肃"},
            "clips": [
                {
                    "start": 0,
                    "end": 15,
                    "hook_text": "很长很长很长很长很长很长",
                    "tts_text": "大家好，今天介绍一个产品。",
                    "caption_style": "fade",
                    "transition_to_next": "fade",
                },
                {
                    "start": 15,
                    "end": 30,
                    "hook_text": "正文",
                    "tts_text": "第二段内容需要足够长才能通过校验规则限制。",
                    "transition_to_next": "fade",
                },
            ],
        },
        "toutiao": {"body": "正文段落"},
    }
    out = enforce_opening_hook_on_copy(copy, brief_hook="测试钩子", title="某产品发布", feed_kind="news")
    c0 = out["douyin"]["clips"][0]
    assert c0["start"] == 0.0
    assert c0["caption_style"] == "spring"
    assert out["douyin"]["effects"]["intro_card"] is True
    assert not str(c0["tts_text"]).startswith("大家好")
    assert out["toutiao"]["body"].split("\n")[0]
