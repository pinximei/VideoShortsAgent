"""Remotion slides 渲染模式。"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.config import PipelineConfig
from pipeline.pipeline_gates import assert_broll_ready, assert_video_plans
from pipeline.slides_render import (
    _resolve_render_style_key,
    brief_to_compose_text,
    is_slides_render_mode,
)


def test_slides_mode_skips_broll_gate():
    cfg = PipelineConfig(render_enabled=True, render_mode="slides")
    assert is_slides_render_mode(cfg)
    assert_broll_ready(cfg)  # 不应抛错


def test_slides_mode_accepts_slides_script(tmp_path: Path):
    cfg = PipelineConfig(
        render_enabled=True,
        render_mode="slides",
        data_dir=tmp_path,
        render_platforms=["douyin"],
    )
    task = tmp_path / "99"
    (task / "llm").mkdir(parents=True)
    (task / "llm" / "slides_script.json").write_text(
        json.dumps({"slides": [{"type": "title_card", "tts_text": "a"}]}),
        encoding="utf-8",
    )
    assert_video_plans(task, cfg)


def test_news_brief_ignores_config_github_dark_style():
    cfg = PipelineConfig(render_visual_style="github_dark", render_scene="ai_news")
    brief = {"feed_kind": "news", "theme_id": "ai_news", "article_id": 885}
    key = _resolve_render_style_key(cfg, brief, "inferno_red")
    assert key == "inferno_red"


def test_brief_to_compose_text():
    text = brief_to_compose_text(
        {"title": "T", "hook": "H", "talking_points": ["p1"], "cta": "c", "detail_url": "u"}
    )
    assert "T" in text and "H" in text and "p1" in text
