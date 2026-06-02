"""主标题禁词与兜底（全链路统一）。"""
from __future__ import annotations

import re
from typing import Any

from python_agent.pinned_template import GENERIC_HERO_FALLBACK, GENERIC_HERO_TITLES

HERO_MAX_CHARS = 14


def is_generic_hero(text: str) -> bool:
    t = re.sub(r"\s+", "", (text or "").strip())
    if not t:
        return False
    return t in GENERIC_HERO_TITLES or len(t) < 2


def sanitize_hero_title(
    text: str,
    *,
    tts: str = "",
    repo_name: str = "",
) -> str:
    """拒绝空洞主标题；优先保留已有具体标题。"""
    t = re.sub(r"\s+", "", (text or "").strip())[:HERO_MAX_CHARS]
    if t and not is_generic_hero(t):
        return t
    from python_agent.douyin_shot_designer import _split_subtitles

    hero, _ = _split_subtitles(tts)
    hero = re.sub(r"\s+", "", hero)[:HERO_MAX_CHARS]
    if hero and not is_generic_hero(hero):
        return hero
    repo = re.sub(r"\s+", " ", (repo_name or "").strip())
    repo = re.split(r"[：:｜|—\-]", repo, maxsplit=1)[0].strip()[:HERO_MAX_CHARS]
    if repo and not is_generic_hero(repo):
        return repo
    return GENERIC_HERO_FALLBACK[:HERO_MAX_CHARS]


def sanitize_slide_hero(slide: dict[str, Any], brief: dict[str, Any] | None = None) -> dict[str, Any]:
    s = dict(slide)
    b = brief or {}
    hero = sanitize_hero_title(
        str(s.get("feature_label") or s.get("heading") or ""),
        tts=str(s.get("tts_text") or ""),
        repo_name=str(b.get("repo_name") or b.get("title") or ""),
    )
    s["feature_label"] = hero
    s["heading"] = hero
    shot = s.get("shot_design")
    if isinstance(shot, dict) and is_generic_hero(str(shot.get("hero_title") or "")):
        shot = dict(shot)
        shot["hero_title"] = hero
        s["shot_design"] = shot
    return s
