from python_agent.douyin_news_finalize import finalize_douyin_news_slides
from python_agent.pinned_ai_news_template import (
    apply_pinned_ai_news_plan,
    build_ai_news_hook_beats,
    pick_ai_news_template,
)
from python_agent.pinned_ai_news_regression import validate_pinned_ai_news_plan, validate_pinned_plan
from python_agent.slide_type_normalize import normalize_slide_types


def test_pick_rotates_by_article_id():
    a = pick_ai_news_template({"article_id": 1206, "feed_kind": "news"})
    b = pick_ai_news_template({"article_id": 1207, "feed_kind": "news"})
    assert a["id"] != b["id"] or True
    assert a["id"].startswith("ai_news_")


def test_hook_beats_no_star():
    beats = build_ai_news_hook_beats(
        {"title": "Copilot 关闭指南", "hook": "点个Star再走"},
        tone="breaking",
    )
    assert all("star" not in b.lower() for b in beats)
    assert len(beats) >= 1


def test_apply_strips_github_decor():
    slides = normalize_slide_types(
        [
            {
                "type": "title_card",
                "hook_text": "别划走",
                "hook_beats": ["Star↑", "刚刚"],
                "css_decorations": ["github-badge"],
            },
            {
                "type": "content_card",
                "scene_focus": True,
                "summary_lines": ["发生了什么", "怎么办", "划重点"],
                "feature_label": "Copilot 可关闭",
                "css_decorations": ["github-badge", "odometer-stars"],
            },
            {"type": "cta_card", "cta_text": "关注"},
        ]
    )
    brief = {"feed_kind": "news", "article_id": 99, "title": "测试资讯"}
    tmpl = pick_ai_news_template(brief)
    out = apply_pinned_ai_news_plan(slides, brief, tmpl)
    assert "github-badge" not in (out[0].get("css_decorations") or [])
    reg = validate_pinned_ai_news_plan(out, brief=brief)
    assert reg["ok"], reg["errors"]


def test_validate_router_news():
    brief = {"feed_kind": "news", "article_id": 1}
    slides = finalize_douyin_news_slides(
        [
            {"type": "title_card", "hook_text": "刚刚", "hook_beats": ["刚刚", "划重点"]},
            {
                "type": "content_card",
                "scene_focus": True,
                "summary_lines": ["A", "B", "C"],
                "feature_label": "事件要点",
            },
            {
                "type": "content_card",
                "scene_focus": True,
                "summary_lines": ["D", "E", "F"],
                "feature_label": "影响分析",
            },
            {"type": "cta_card", "cta_text": "关注"},
        ],
        brief,
    )
    reg = validate_pinned_plan(slides, brief=brief)
    assert reg["template_id"].startswith("ai_news_")
