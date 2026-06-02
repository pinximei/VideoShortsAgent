from python_agent.capabilities.opening_hook import (
    enforce_opening_hook_on_copy,
    enforce_opening_hook_on_slides_script,
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


def test_enforce_slides_title_opening() -> None:
    script = {
        "slides": [
            {
                "type": "title_card",
                "heading": "Star破万",
                "tts_text": "大家好，今天介绍 GitHub 项目。",
                "hook_text": "",
            }
        ]
    }
    out = enforce_opening_hook_on_slides_script(
        script,
        brief={"title": "某神器", "hook": "别划走", "feed_kind": "github_daily"},
        platform="douyin",
    )
    s0 = out["slides"][0]
    assert s0.get("opening_burst") is True
    assert s0.get("hook_text")
    assert not str(s0["tts_text"]).startswith("大家好")
    assert str(s0["tts_text"]).count("。") <= 1
    assert not s0.get("suppress_opening_caption")
    assert len(s0.get("hook_beats") or []) <= 2
