from python_agent.douyin_news_finalize import finalize_douyin_news_slides
from python_agent.ai_news_visual import apply_variant_visual_dna
from python_agent.pinned_ai_news_template import (
    apply_pinned_ai_news_plan,
    build_ai_news_hook_beats,
    list_ai_news_bases,
    list_ai_news_variants,
    pick_ai_news_template,
)
from python_agent.pinned_ai_news_regression import validate_pinned_ai_news_plan, validate_pinned_plan
from python_agent.slide_type_normalize import normalize_slide_types


def test_pick_production_default_without_explicit():
    t = pick_ai_news_template({"article_id": 1206, "feed_kind": "news"})
    assert t["id"] == "ai_news_void_signal"


def test_pick_rotates_when_pool_not_fixed():
    a = pick_ai_news_template(
        {"article_id": 1206, "feed_kind": "news", "ai_news_rotation_pool": "bases"}
    )
    b = pick_ai_news_template(
        {"article_id": 1207, "feed_kind": "news", "ai_news_rotation_pool": "bases"}
    )
    assert a["id"].startswith("ai_news_")
    assert b["id"].startswith("ai_news_")


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


def test_variants_have_distinct_gradients():
    bases = list_ai_news_bases()
    grads = [tuple(v.get("gradient_colors") or []) for v in bases]
    moods = {str(v.get("color_mood") or "") for v in bases}
    bgs = {str(v.get("background_variant") or "") for v in bases}
    assert len(bases) >= 9
    assert len(set(grads)) == len(grads)
    assert len(moods) >= 8
    assert len(bgs) >= 6


def test_nine_bases_and_eighteen_derivatives():
    all_v = list_ai_news_variants()
    bases = list_ai_news_bases()
    deriv = list_ai_news_variants(tier="derivative")
    assert len(bases) == 9
    assert len(deriv) == 18
    assert len(all_v) == 27
    for d in deriv:
        assert d.get("parent_id"), d.get("id")


def test_production_default_is_stable_across_articles():
    seen = {
        pick_ai_news_template({"article_id": i, "feed_kind": "news"}).get("id")
        for i in range(1, 120)
    }
    assert seen == {"ai_news_void_signal"}


def test_rotation_uses_bases_only_when_pool_bases():
    seen = {
        pick_ai_news_template(
            {"article_id": i, "feed_kind": "news", "ai_news_rotation_pool": "bases"}
        ).get("id")
        for i in range(1, 120)
    }
    assert all(str(x).startswith("ai_news_") for x in seen)
    assert not any(str(x).endswith("_snap") or str(x).endswith("_rush") for x in seen)


def test_full_pool_includes_derivatives():
    ids = {
        pick_ai_news_template(
            {"article_id": i, "feed_kind": "news", "ai_news_rotation_pool": "all"}
        ).get("id")
        for i in range(1, 400)
    }
    assert any(str(x).endswith("_snap") for x in ids)
    assert any(str(x).endswith("_rush") for x in ids)


def test_apply_variant_visual_dna_writes_colors():
    tmpl = list_ai_news_variants()[0]
    out = apply_variant_visual_dna([{"type": "title_card"}], tmpl)
    assert out[0]["visual_design"]["colors"] == tmpl["gradient_colors"]
    assert out[0]["visual_design"].get("use_web3_background") is True


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
