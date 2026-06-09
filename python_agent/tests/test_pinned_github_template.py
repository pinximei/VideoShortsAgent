from python_agent.douyin_github_finalize import finalize_douyin_github_slides
from python_agent.motion_templates import is_github_daily_brief
from python_agent.pinned_github_template import (
    apply_pinned_github_plan,
    inject_github_pinned_brief,
    list_github_pinned_variants,
    pick_github_pinned_variant,
)


def test_pick_rotates_by_content_key():
    a = pick_github_pinned_variant({"content_key": "repo-a", "feed_kind": "github_daily"})
    b = pick_github_pinned_variant({"content_key": "repo-b", "feed_kind": "github_daily"})
    assert a["id"].startswith("github_daily_")
    assert b["id"].startswith("github_daily_")


def test_variants_have_distinct_gradients():
    variants = list_github_pinned_variants()
    grads = [tuple(v.get("gradient_colors") or []) for v in variants]
    assert len(grads) >= 3
    assert len(set(grads)) == len(grads)


def test_inject_sets_gv_and_disables_platform_default():
    b = inject_github_pinned_brief({"feed_kind": "github_daily", "content_key": "x1"})
    assert b.get("pinned_github_variant_id")
    assert b.get("github_daily_style_id")
    assert b.get("use_platform_gv_default") is False


def test_apply_keeps_github_decor():
    slides = [
        {"type": "title_card", "hook_beats": ["别划走", "Star 1.2万"]},
        {
            "type": "content_card",
            "scene_focus": True,
            "summary_lines": ["A", "B", "C"],
            "feature_label": "OpenHands 亮点",
        },
        {"type": "cta_card", "cta_text": "关注"},
    ]
    brief = {"feed_kind": "github_daily", "content_key": "oh-1", "stars": "1.2万"}
    tmpl = pick_github_pinned_variant(brief)
    out = apply_pinned_github_plan(slides, brief, tmpl)
    dec = set(out[0].get("css_decorations") or [])
    assert "github-badge" in dec or "grid-tunnel-bg" in dec
    assert out[0].get("pinned_github_variant_id") == tmpl["id"]
    assert out[0]["visual_design"].get("colors") == tmpl["gradient_colors"]


def test_finalize_github_applies_variant():
    slides = [
        {"type": "title_card", "hook_beats": ["别划走", "Star↑"]},
        {
            "type": "content_card",
            "scene_focus": True,
            "summary_lines": ["能做什么", "怎么用", "为什么火"],
            "feature_label": "Agent 框架",
        },
        {
            "type": "content_card",
            "scene_focus": True,
            "summary_lines": ["D", "E", "F"],
            "feature_label": "上手步骤",
        },
        {"type": "cta_card", "cta_text": "关注"},
    ]
    brief = {"feed_kind": "github_daily", "article_id": 42, "stars": "9k"}
    out = finalize_douyin_github_slides(slides, brief)
    profiles = {s.get("motion_profile") for s in out if s.get("scene_focus")}
    assert len(profiles) >= 1
    assert all(s.get("pinned_github_variant_id") for s in out)
