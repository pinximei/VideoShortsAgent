"""口播/语速 20 套模板选型。"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python_agent.voice_content_templates import (
    load_voice_catalog,
    pick_voice_content_style,
    voice_style_prompt_block,
)


def test_catalog_has_20():
    assert len(load_voice_catalog().get("styles") or []) == 20


def test_pick_stable():
    brief = {"article_id": "885", "feed_kind": "github"}
    a = pick_voice_content_style(brief)
    b = pick_voice_content_style(brief)
    assert a["id"] == b["id"]


def test_prompt_block():
    s = pick_voice_content_style({"feed_kind": "news", "title": "x"})
    block = voice_style_prompt_block(s)
    assert "口播风格模板" in block
    assert "禁止开场" in block
