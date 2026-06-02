"""中区内容与底栏口播的安全区碰撞检测与自动修正。"""
from __future__ import annotations

from typing import Any

# 竖屏 1080x1920 近似
DEFAULT_HEIGHT = 1920
DEFAULT_WIDTH = 1080
MIN_GAP_PX = 48
HERO_LINE_PX = 96
SUBTITLE_ROW_PX = 88
SUBTITLE_GAP_PX = 38
ICON_PX = 56
VIZ_BLOCK_PX = 220


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


def fix_slide_layout_collision(slide: dict[str, Any], *, height: int = DEFAULT_HEIGHT) -> dict[str, Any]:
    s = dict(slide)
    if not _is_content_slide(s):
        return s
    report = check_slide_layout_collision(s, height=height)
    if report["ok"]:
        return s
    mp = dict(s.get("motion_params") or {})
    lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
    vt = str(s.get("viz_type") or "none").lower()

    if "mid_block_too_tall" in str(report["issues"]):
        mp["midSafeBottomRatio"] = max(float(mp.get("midSafeBottomRatio") or 0.40), 0.44)
        mp["midHeroFontScale"] = min(float(mp.get("midHeroFontScale") or 1.0), 0.9)

    if "caption_mid_gap" in str(report["issues"]):
        mp["midSafeBottomRatio"] = min(0.48, float(mp.get("midSafeBottomRatio") or 0.40) + 0.04)
        mp["captionBottomPx"] = max(int(mp.get("captionBottomPx") or 300), 320)

    s["motion_params"] = mp
    s["_layout_collision_fixed"] = True
    return s


def fix_all_layout_collisions(
    slides: list[dict[str, Any]],
    *,
    height: int = DEFAULT_HEIGHT,
) -> list[dict[str, Any]]:
    return [fix_slide_layout_collision(s, height=height) for s in slides]
