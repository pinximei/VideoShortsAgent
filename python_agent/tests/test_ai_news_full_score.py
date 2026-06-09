from python_agent.ai_news_full_score import ensure_ai_news_slides_for_100
from python_agent.render_quality_score import score_douyin_render


def test_ensure_cta_and_score_100():
    slides = [
        {"type": "title_card", "hook_beats": ["a"], "tts_text": "标题"},
        {"type": "content_card", "scene_focus": True, "motion_profile": "glass_card_stack", "summary_lines": ["1"]},
        {"type": "content_card", "scene_focus": True, "motion_profile": "glass_card_stack", "summary_lines": ["2"]},
    ]
    brief = {"feed_kind": "news", "article_id": 1, "cta": "关注"}
    out = ensure_ai_news_slides_for_100(slides, brief)
    assert str(out[-1].get("type")) == "cta_card"
    profiles = {s.get("motion_profile") for s in out if s.get("scene_focus")}
    assert len(profiles) >= 2
    sc = score_douyin_render(out, brief=brief, gate={"ok": True})
    assert sc["score"] == 100
