"""渲染前幻灯片质量门禁：字幕、图表、中部信息密度。"""
from __future__ import annotations

import re
from typing import Any

from python_agent.caption_timeline import validate_caption_pages
from python_agent.display_text import find_unsafe_caption_splits

_VIZ_TYPES = frozenset({"none", "line", "bar", "stat"})
_MID_INFO = frozenset({"steps", "compare", "keywords", "none"})


def _is_content_slide(s: dict[str, Any]) -> bool:
    return bool(s.get("scene_focus")) or str(s.get("type")) == "content_card"


def auto_fix_slides(slides: list[dict[str, Any]], *, platform: str = "douyin") -> list[dict[str, Any]]:
    """自动修补可安全修复的问题（不调用 LLM）。"""
    out: list[dict[str, Any]] = []
    content_idx = 0
    for s in slides:
        slide = dict(s)
        if _is_content_slide(slide):
            vt = str(slide.get("viz_type") or "none").lower()
            series = list(slide.get("chart_series") or slide.get("chart_bars") or [])
            nums = [x for x in series if isinstance(x, (int, float)) and x > 0]
            if vt == "line" and len(nums) < 3:
                slide["viz_type"] = "none"
                slide["show_chart"] = False
                slide["chart_series"] = []
            elif vt == "bar" and len(nums) < 2:
                slide["viz_type"] = "none"
                slide["show_chart"] = False
            elif vt == "stat" and not str(slide.get("stat_value") or "").strip():
                slide["viz_type"] = "none"

            lines = [str(x).strip() for x in (slide.get("summary_lines") or []) if str(x).strip()]
            if not lines:
                heading = str(slide.get("heading") or slide.get("feature_label") or "核心亮点")
                slide["summary_lines"] = [heading[:14], "值得收藏"]
            kin = [str(x).strip() for x in (slide.get("kinetic_phrases") or []) if str(x).strip()]
            if not kin and str(slide.get("viz_type") or "none") == "none":
                slide["kinetic_phrases"] = ["开源", "好用", "收藏"]
                slide["show_kinetic_wall"] = True

            layout = str(slide.get("mid_info_layout") or "none").lower()
            if layout not in _MID_INFO or layout == "none":
                layouts = ("keywords", "steps", "compare", "keywords")
                slide["mid_info_layout"] = layouts[content_idx % len(layouts)]

            slide.setdefault("caption_use_tts_timeline", True)
            content_idx += 1

        if str(slide.get("type")) == "title_card":
            slide.setdefault("opening_duration_frames", 100 if platform == "douyin" else 120)
            beats = slide.get("hook_beats") or []
            if not beats:
                hook = str(slide.get("hook_text") or slide.get("heading") or "别划走")
                slide["hook_beats"] = [hook[:18]]

        slide.setdefault("caption_use_tts_timeline", True)
        out.append(slide)
    return out


def validate_slides_before_render(
    slides: list[dict[str, Any]],
    *,
    platform: str = "douyin",
    strict: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    empty_mid_run = 0
    for i, s in enumerate(slides):
        tts = str(s.get("tts_text") or "").strip()
        if not tts and s.get("type") != "cta_card":
            warnings.append(f"slide_{i}_missing_tts")

        if _is_content_slide(s):
            lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
            if not lines:
                empty_mid_run += 1
                warnings.append(f"slide_{i}_empty_summary_lines")
            else:
                empty_mid_run = 0

            vt = str(s.get("viz_type") or "none")
            if vt not in _VIZ_TYPES:
                errors.append(f"slide_{i}_invalid_viz:{vt}")

            if vt == "line" and len(s.get("chart_series") or []) < 3:
                errors.append(f"slide_{i}_line_without_series")

        raw_pages = s.get("_caption_pages_preview")
        if isinstance(raw_pages, list) and raw_pages:
            issues = validate_caption_pages(raw_pages)
            warnings.extend(issues)

    if empty_mid_run >= 2:
        warnings.append("consecutive_empty_mid_content")

    tts_texts = [str(s.get("tts_text") or "") for s in slides if s.get("tts_text")]
    for phrase in find_unsafe_caption_splits(tts_texts):
        warnings.append(f"unsafe_tts_split:{phrase}")

    ok = not errors if strict else len(errors) == 0
    return {
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "platform": platform,
        "slide_count": len(slides),
    }


def attach_caption_preview(slides: list[dict[str, Any]], tts_clips: list[dict]) -> list[dict[str, Any]]:
    """为门禁写入 _caption_pages_preview（不落盘到最终 props）。"""
    from python_agent.caption_timeline import prepare_slide_captions

    out = []
    for i, s in enumerate(slides):
        slide = dict(s)
        tts = tts_clips[i] if i < len(tts_clips) else {}
        raw = tts.get("sentences") or []
        _, pages = prepare_slide_captions(raw, slide, platform=str(slide.get("platform") or "douyin"))
        slide["_caption_pages_preview"] = pages
        out.append(slide)
    return out
