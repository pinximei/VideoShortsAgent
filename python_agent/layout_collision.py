"""中区内容与底栏口播的安全区碰撞检测与自动修正。"""
from __future__ import annotations

from typing import Any

from python_agent.subtitle_copy import SUBTITLE_MAX_CHARS

# 竖屏 1080x1920 近似
DEFAULT_HEIGHT = 1920
DEFAULT_WIDTH = 1080
MIN_GAP_PX = 48
HERO_LINE_PX = 96
SUBTITLE_ROW_PX = 88
SUBTITLE_GAP_PX = 38
ICON_PX = 56
VIZ_BLOCK_PX = 220
_MAX_FIX_ROUNDS = 8


def _is_content_slide(s: dict[str, Any]) -> bool:
    return bool(s.get("scene_focus")) or str(s.get("type")) == "content_card"


def estimate_mid_block_height(slide: dict[str, Any]) -> int:
    """估算中区内容块占用高度（px）。"""
    h = 0
    if str(slide.get("mid_icon") or "").strip():
        h += ICON_PX
    h += HERO_LINE_PX
    lines = [str(x).strip() for x in (slide.get("summary_lines") or []) if str(x).strip()]
    vt = str(slide.get("viz_type") or "none").lower()
    if vt in ("stat", "line", "bar"):
        h += VIZ_BLOCK_PX
        lines = lines[:2]
    n = len(lines)
    if n:
        h += 28 + n * SUBTITLE_ROW_PX + max(0, n - 1) * SUBTITLE_GAP_PX
    return h


def mid_zone_bounds(
    slide: dict[str, Any],
    *,
    height: int = DEFAULT_HEIGHT,
) -> tuple[int, int]:
    mp = slide.get("motion_params") or {}
    top_ratio = float(mp.get("midSafeTopRatio") or 0.14)
    bottom_ratio = float(mp.get("midSafeBottomRatio") or 0.40)
    safe_top = int(height * top_ratio)
    safe_bottom = int(height * bottom_ratio)
    zone_h = max(200, height - safe_top - safe_bottom)
    return zone_h, safe_bottom


def caption_zone_top_px(
    slide: dict[str, Any],
    *,
    height: int = DEFAULT_HEIGHT,
) -> int:
    mp = slide.get("motion_params") or {}
    caption_bottom = int(mp.get("captionBottomPx") or 300)
    bottom_ratio = float(mp.get("midSafeBottomRatio") or 0.40)
    return int(height - height * bottom_ratio - caption_bottom)


def check_slide_layout_collision(
    slide: dict[str, Any],
    *,
    height: int = DEFAULT_HEIGHT,
) -> dict[str, Any]:
    if not _is_content_slide(slide):
        return {"ok": True, "gap_px": 999, "issues": []}
    zone_h, _ = mid_zone_bounds(slide, height=height)
    block_h = estimate_mid_block_height(slide)
    cap_top = caption_zone_top_px(slide, height=height)
    mid_top = int(height * float((slide.get("motion_params") or {}).get("midSafeTopRatio") or 0.14))
    mid_bottom_y = mid_top + zone_h
    gap = cap_top - mid_bottom_y
    issues: list[str] = []
    if block_h > zone_h - 40:
        issues.append(f"mid_block_too_tall:{block_h}>{zone_h}")
    if gap < MIN_GAP_PX:
        issues.append(f"caption_mid_gap:{gap}px<{MIN_GAP_PX}px")
    return {
        "ok": not issues,
        "gap_px": gap,
        "block_h": block_h,
        "zone_h": zone_h,
        "issues": issues,
    }


def _trim_summary_lines(slide: dict[str, Any], *, max_lines: int) -> None:
    lines = [str(x).strip()[:SUBTITLE_MAX_CHARS] for x in (slide.get("summary_lines") or []) if str(x).strip()]
    if len(lines) > max_lines:
        slide["summary_lines"] = lines[:max_lines]


def _apply_collision_tweaks(slide: dict[str, Any], issues: list[str]) -> None:
    mp = dict(slide.get("motion_params") or {})
    issue_blob = " ".join(issues)

    if "mid_block_too_tall" in issue_blob:
        mp["midSafeBottomRatio"] = max(float(mp.get("midSafeBottomRatio") or 0.40), 0.44)
        mp["midHeroFontScale"] = min(float(mp.get("midHeroFontScale") or 1.0), 0.88)
        vt = str(slide.get("viz_type") or "none").lower()
        if vt == "stat" and len(slide.get("summary_lines") or []) >= 3:
            slide["viz_type"] = "none"
            slide["show_chart"] = False
        elif len(slide.get("summary_lines") or []) > 3:
            _trim_summary_lines(slide, max_lines=3)

    if "caption_mid_gap" in issue_blob:
        mp["midSafeBottomRatio"] = min(0.50, float(mp.get("midSafeBottomRatio") or 0.40) + 0.05)
        mp["captionBottomPx"] = max(int(mp.get("captionBottomPx") or 300), 340)

    lines = [str(x).strip()[:SUBTITLE_MAX_CHARS] for x in (slide.get("summary_lines") or []) if str(x).strip()]
    slide["summary_lines"] = lines
    slide["motion_params"] = mp


def fix_slide_layout_collision(slide: dict[str, Any], *, height: int = DEFAULT_HEIGHT) -> dict[str, Any]:
    s = dict(slide)
    if not _is_content_slide(s):
        return s
    if str(s.get("type")) == "cta_card":
        s["suppress_bottom_caption"] = True
        return s

    for _ in range(_MAX_FIX_ROUNDS):
        report = check_slide_layout_collision(s, height=height)
        if report["ok"]:
            break
        _apply_collision_tweaks(s, list(report.get("issues") or []))
        s["_layout_collision_fixed"] = True

    if not check_slide_layout_collision(s, height=height).get("ok"):
        _trim_summary_lines(s, max_lines=2)
        mp = dict(s.get("motion_params") or {})
        mp["midSafeBottomRatio"] = 0.50
        mp["captionBottomPx"] = max(int(mp.get("captionBottomPx") or 300), 360)
        s["motion_params"] = mp
        s["_layout_collision_fixed"] = True

    return s


def fix_all_layout_collisions(
    slides: list[dict[str, Any]],
    *,
    height: int = DEFAULT_HEIGHT,
) -> list[dict[str, Any]]:
    return [fix_slide_layout_collision(s, height=height) for s in slides]
