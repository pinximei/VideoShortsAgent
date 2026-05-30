"""口播可渲染性判断、分平台文案裁剪。"""
from __future__ import annotations

import copy
import re
from typing import Any

from .platform_presets import PlatformPreset

_URL_RE = re.compile(r"https?://[^\s\]\)\"'<>]+|www\.[^\s\]\)\"'<>]+", re.I)

MIN_RENDER_TOTAL_CHARS = 40
MIN_RENDER_HOOK_CHARS = 4

# 平台口播字数上限（生成 clips 前裁剪，配合 max_seconds 控总长）
PLATFORM_COPY_LIMITS: dict[str, dict[str, int | float]] = {
    "douyin": {
        "max_points": 3,
        "hook_chars": 42,
        "point_chars": 68,
        "cta_chars": 36,
        "max_seconds": 45.0,
    },
    "xhs": {
        "max_points": 4,
        "hook_chars": 56,
        "point_chars": 88,
        "cta_chars": 48,
        "max_seconds": 55.0,
    },
}


def _plain(text: str) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    s = _URL_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def truncate_sentence(text: str, max_chars: int) -> str:
    s = (text or "").strip().replace("\n", " ")
    if len(s) <= max_chars:
        return s
    return s[: max(1, max_chars - 1)].rstrip() + "…"


def brief_renderable_char_count(brief: dict[str, Any]) -> int:
    parts = [
        brief.get("hook") or "",
        *(brief.get("talking_points") or []),
        brief.get("cta") or "",
        brief.get("title") or "",
    ]
    return len(_plain(" ".join(str(p) for p in parts if p)))


def brief_is_renderable(brief: dict[str, Any]) -> tuple[bool, str]:
    """口播包是否足以生成视频（非仅标题/链接）。"""
    hook = _plain(str(brief.get("hook") or ""))
    if len(hook) < MIN_RENDER_HOOK_CHARS:
        return False, f"钩子过短（{len(hook)} 字）"
    total = brief_renderable_char_count(brief)
    if total < MIN_RENDER_TOTAL_CHARS:
        return False, f"口播总实质字数 {total} < {MIN_RENDER_TOTAL_CHARS}，跳过渲染"
    points = [p for p in (brief.get("talking_points") or []) if _plain(str(p))]
    if not points and len(hook) < 20:
        return False, "无有效要点且钩子不足以撑起成片"
    return True, ""


def brief_for_platform(brief: dict[str, Any], preset: PlatformPreset) -> dict[str, Any]:
    """按平台节奏裁剪 hook / 要点 / CTA，返回新 dict。"""
    lim = PLATFORM_COPY_LIMITS.get(preset.id, PLATFORM_COPY_LIMITS["douyin"])
    out = copy.deepcopy(brief)
    out["hook"] = truncate_sentence(str(out.get("hook") or out.get("title") or ""), int(lim["hook_chars"]))
    max_pts = int(lim["max_points"])
    pts = [
        truncate_sentence(str(p), int(lim["point_chars"]))
        for p in (out.get("talking_points") or [])
        if str(p).strip()
    ][:max_pts]
    out["talking_points"] = pts
    out["cta"] = truncate_sentence(str(out.get("cta") or "详情见简介"), int(lim["cta_chars"]))
    return out


def effective_max_seconds(preset: PlatformPreset) -> float:
    lim = PLATFORM_COPY_LIMITS.get(preset.id)
    if lim and lim.get("max_seconds"):
        return min(float(preset.max_seconds or 60), float(lim["max_seconds"]))
    return float(preset.max_seconds or 60)
