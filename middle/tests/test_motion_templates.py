"""动效母版目录选型。"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python_agent.motion_templates import (
    apply_template_plan_to_slides,
    build_github_daily_slide_plan,
    build_slide_template_plan,
    is_github_daily_brief,
    load_catalog,
    load_github_daily_catalog,
    pick_template_for_slide,
)


def test_catalog_has_many_templates():
    cat = load_catalog()
    templates = cat.get("templates") or []
    assert len(templates) >= 100
    assert cat.get("version") == 2


def test_pick_template_stable():
    a = pick_template_for_slide("article-885", 0, "title_card")
    b = pick_template_for_slide("article-885", 0, "title_card")
    assert a["id"] == b["id"]
    assert a.get("motion_profile")


def test_news_feed_prefers_tiktok_profiles():
    t = pick_template_for_slide("article-885", 0, "title_card", feed_kind="news")
    prof = t.get("motion_profile") or ""
    assert prof in (
        "tiktok_word_pop",
        "tiktok_phrase_pages",
        "kinetic_slam_tight",
        "flash_hook_smash",
        "glitch_hook_clean",
        "minimal_headline",
        "shake_emphasis",
    )


def test_apply_plan_to_slides():
    slides = [{"type": "title_card", "tts_text": "x"}, {"type": "content_card", "tts_text": "y"}]
    brief = {"article_id": 885, "feed_kind": "news"}
    out = apply_template_plan_to_slides(slides, brief)
    assert out[0].get("motion_template_id")
    assert out[0]["visual_design"].get("motion_profile")


def test_catalog_file_exists():
    path = Path(__file__).resolve().parents[2] / "templates" / "motion_templates" / "catalog.json"
    assert path.is_file()


def test_build_plan_length():
    slides = [{"type": "title_card"}, {"type": "content_card"}, {"type": "cta_card"}]
    plan = build_slide_template_plan({"article_id": 1}, slides)
    assert len(plan) == 3


def test_github_daily_catalog_has_20():
    cat = load_github_daily_catalog()
    assert len(cat.get("styles") or []) == 20


def test_github_daily_plan_unified_style():
    slides = [
        {"type": "title_card"},
        {"type": "content_card"},
        {"type": "cta_card"},
    ]
    brief = {"article_id": "gh-001", "feed_kind": "github"}
    assert is_github_daily_brief(brief)
    picked, plan = build_github_daily_slide_plan(brief, slides)
    assert picked.get("id")
    ids = {p.get("github_daily_style_id") for p in plan}
    assert len(ids) == 1
    out = apply_template_plan_to_slides([dict(s) for s in slides], brief)
    assert out[0].get("css_decorations") is not None
    assert out[0].get("background_color")
