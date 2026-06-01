"""抖音 / 小红书默认 G+V 配对（爆款基线）。"""
from __future__ import annotations

from typing import Any

# 抖音：快钩子 + 砸字；小红书：极简白底 + 柔和讲解
PLATFORM_GV: dict[str, dict[str, str]] = {
    "douyin": {
        "voice_id": "V01_burst_hook_fast",
        "motion_id": "G01_cyber_hook_yellow",
    },
    "xhs": {
        "voice_id": "V04_minimal_calm",
        "motion_id": "G03_minimal_white_series",
    },
}


def _find_by_id(items: list[dict[str, Any]], sid: str) -> dict[str, Any] | None:
    for it in items:
        if it.get("id") == sid:
            return dict(it)
    return None


def resolve_platform_voice_style(
    brief: dict[str, Any],
    styles: list[dict[str, Any]],
) -> dict[str, Any] | None:
    platform = str(brief.get("platform") or "").strip().lower()
    explicit = str(brief.get("voice_content_style_id") or "").strip()
    if explicit:
        return _find_by_id(styles, explicit)
    defaults = PLATFORM_GV.get(platform) or {}
    if defaults.get("voice_id"):
        return _find_by_id(styles, defaults["voice_id"])
    motion_id = str(brief.get("github_daily_style_id") or "")
    if motion_id:
        for s in styles:
            ref = str(s.get("reference_motion") or "")
            if ref and motion_id.startswith(ref):
                return dict(s)
    return None


def resolve_platform_motion_style(
    brief: dict[str, Any],
    styles: list[dict[str, Any]],
) -> dict[str, Any] | None:
    platform = str(brief.get("platform") or "").strip().lower()
    explicit = str(brief.get("github_daily_style_id") or brief.get("motion_style_id") or "").strip()
    if explicit:
        return _find_by_id(styles, explicit)
    defaults = PLATFORM_GV.get(platform) or {}
    if defaults.get("motion_id"):
        return _find_by_id(styles, defaults["motion_id"])
    voice_id = str(brief.get("voice_content_style_id") or "")
    if voice_id:
        from python_agent.voice_content_templates import load_voice_catalog

        v = _find_by_id(list(load_voice_catalog().get("styles") or []), voice_id)
        ref = str((v or {}).get("reference_motion") or "")
        if ref:
            for s in styles:
                if str(s.get("id") or "").startswith(ref):
                    return dict(s)
    return None
