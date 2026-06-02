from python_agent.capabilities.opening_hook import enforce_opening_hook_on_slides_script


def test_github_daily_title_gets_two_beats():
    script = {
        "slides": [
            {
                "type": "title_card",
                "tts_text": "今天介绍 OpenHands。",
                "heading": "OpenHands",
            },
            {"type": "content_card", "scene_focus": True},
        ]
    }
    brief = {
        "feed_kind": "github_daily",
        "repo_name": "OpenHands",
        "stars": "12000",
        "title": "OpenHands",
    }
    out = enforce_opening_hook_on_slides_script(script, brief=brief, platform="douyin")
    beats = out["slides"][0].get("hook_beats") or []
    assert len(beats) >= 1
    assert int(out["slides"][0].get("opening_duration_frames") or 0) <= 84
