"""渲染前幻灯片质量门禁：字幕、图表、中部信息密度。"""
from __future__ import annotations

import re
from typing import Any

from python_agent.caption_timeline import validate_caption_pages
from python_agent.display_text import find_unsafe_caption_splits
from python_agent.layout_collision import check_slide_layout_collision, fix_all_layout_collisions
from python_agent.subtitle_copy import (
    SUBTITLE_MAX_CHARS,
    SUBTITLE_MIN_CHARS,
    ensure_douyin_content_diversity,
    normalize_slide_mid_copy,
)

_MAX_HOOK_BEATS = 2
_MAX_OPENING_BURST_FRAMES = 84  # 2.8s @30fps
from python_agent.tts_copy_rules import validate_slides_tts_copy

_VIZ_TYPES = frozenset({"none", "line", "bar", "stat"})
_MID_INFO = frozenset({"steps", "compare", "keywords", "framed", "none"})


def _is_content_slide(s: dict[str, Any]) -> bool:
    return bool(s.get("scene_focus")) or str(s.get("type")) == "content_card"


def auto_fix_slides(
    slides: list[dict[str, Any]],
    *,
    platform: str = "douyin",
    brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
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

            slide = normalize_slide_mid_copy(slide)
            lines = [str(x).strip() for x in (slide.get("summary_lines") or []) if str(x).strip()]
            if not lines:
                slide["summary_lines"] = ["核心能力", "一步上手", "值得收藏"]
            elif len(lines) < 3:
                for fb in ("省时省力", "值得收藏", "立刻见效", "一步上手"):
                    if len(lines) >= 4:
                        break
                    if fb not in lines:
                        lines.append(fb)
                slide["summary_lines"] = lines[:4]
            slide.setdefault("mid_info_layout", "framed")
            if str(slide.get("tts_text") or "").find("自然语言") >= 0:
                slide["mid_effect"] = "liquid_shake"
            kin = [str(x).strip() for x in (slide.get("kinetic_phrases") or []) if str(x).strip()]
            if not kin and str(slide.get("viz_type") or "none") == "none":
                slide["kinetic_phrases"] = ["开源", "好用", "收藏"]
                slide["show_kinetic_wall"] = True

            layout = str(slide.get("mid_info_layout") or "none").lower()
            if layout not in _MID_INFO:
                slide["mid_info_layout"] = "framed"
            elif layout == "none":
                slide["mid_info_layout"] = "framed"

            slide.setdefault("caption_use_tts_timeline", True)
            content_idx += 1

        if str(slide.get("type")) == "title_card":
            beats = [
                str(x).strip()[:18]
                for x in (slide.get("hook_beats") or [])
                if str(x).strip()
            ]
            if not beats:
                hook = str(slide.get("hook_text") or slide.get("heading") or "别划走")
                beats = [hook[:18]]
            slide["hook_beats"] = beats[:_MAX_HOOK_BEATS]
            burst = int(slide.get("opening_duration_frames") or _MAX_OPENING_BURST_FRAMES)
            slide["opening_duration_frames"] = min(burst, _MAX_OPENING_BURST_FRAMES)

        if platform == "xhs":
            mp = slide.get("motion_params") or {}
            bottom = int(mp.get("captionBottomPx") or 0)
            if bottom and bottom < 360:
                slide.setdefault("_layout_fix", True)
                mp = dict(mp)
                mp["captionBottomPx"] = 400
                mp.setdefault("midSafeBottomRatio", 0.52)
                slide["motion_params"] = mp

        slide.setdefault("caption_use_tts_timeline", True)
        out.append(slide)
    for i, slide in enumerate(out):
        if platform == "douyin" and _is_content_slide(slide):
            slide.setdefault("transition_to_next", "dissolve")
        if i + 1 < len(out) and str(out[i + 1].get("type") or "") == "cta_card":
            slide["transition_to_next"] = "dissolve"
        if str(slide.get("type") or "") == "cta_card":
            slide["mid_info_layout"] = "none"
            slide["viz_type"] = "none"
            slide["show_chart"] = False
    _ensure_github_viz(out, brief)
    from python_agent.douyin_shot_stylist import sync_github_stars_on_slides

    sync_github_stars_on_slides(out, brief)
    for slide in out:
        if _is_content_slide(slide):
            from python_agent.douyin_shot_stylist import resolve_content_hero_title

            hero = resolve_content_hero_title(slide, brief)
            slide["feature_label"] = hero
            slide["heading"] = hero
    out = fix_all_layout_collisions(out)
    if platform == "douyin":
        out = ensure_douyin_content_diversity(out)
    return out


def _brief_wants_github_viz(brief: dict[str, Any] | None) -> bool:
    b = brief or {}
    fk = str(b.get("feed_kind") or "").lower()
    if fk in ("github", "github_daily", "daily_github", "github_trending"):
        return True
    stars = str(b.get("stars") or b.get("star_count") or "").strip()
    blob = " ".join(
        str(b.get(k) or "")
        for k in ("title", "repo_name", "hook", "description")
    )
    if stars:
        return True
    return bool(re.search(r"github|star|stars|⭐|热度|trend|trending", blob, re.I))


def _ensure_github_viz(slides: list[dict[str, Any]], brief: dict[str, Any] | None) -> None:
    if not _brief_wants_github_viz(brief):
        return
    stars = str((brief or {}).get("stars") or (brief or {}).get("star_count") or "12k+").strip()
    content_i = 0
    for i, s in enumerate(slides):
        if not _is_content_slide(s):
            continue
        if content_i == 0 and str(s.get("viz_type") or "none") == "none":
            plat = str((brief or {}).get("platform") or s.get("platform") or "").lower()
            card_layout = (
                plat == "douyin"
                or str(s.get("motion_profile") or "") == "glass_card_stack"
            )
            force_stat = bool(stars) and re.search(r"\d|k|万|⭐", stars, re.I)
            if force_stat and not card_layout:
                s["viz_type"] = "stat"
                s["stat_value"] = stars[:12]
                s["show_kinetic_wall"] = False
                s["show_chart"] = False
            elif card_layout and not force_stat:
                lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
                hot_line = f"Star {stars[:8]}" if stars else "GitHub 近期很火"
                if stars and not any("火" in x or "热" in x or "star" in x.lower() for x in lines):
                    lines = (lines + [hot_line])[:3] if lines else ["解决什么问题", hot_line]
                    s["summary_lines"] = lines
                slides[i] = normalize_slide_mid_copy(s)
            else:
                s["viz_type"] = "stat"
                s["stat_value"] = stars[:12] if stars else "12k+"
                s["show_kinetic_wall"] = False
                s["show_chart"] = False
                lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
                if len(lines) > 2:
                    s["summary_lines"] = lines[:2]
        content_i += 1


def summarize_quality_gate(gate: dict[str, Any]) -> str:
    """人类可读的门禁摘要（写入 JSON summary 字段）。"""
    lines: list[str] = []
    if gate.get("ok"):
        lines.append("门禁通过，可进入渲染。")
    else:
        lines.append("门禁未通过，需修复后再渲染。")
    errs = gate.get("errors") or []
    warns = gate.get("warnings") or []
    if errs:
        lines.append(f"错误 {len(errs)} 项: " + "；".join(str(e) for e in errs[:6]))
        if len(errs) > 6:
            lines.append(f"  …另有 {len(errs) - 6} 项错误")
    if warns:
        lines.append(f"警告 {len(warns)} 项: " + "；".join(str(w) for w in warns[:5]))
        if len(warns) > 5:
            lines.append(f"  …另有 {len(warns) - 5} 项警告")
    lines.append(f"平台={gate.get('platform', '?')} 镜数={gate.get('slide_count', '?')}")
    return "\n".join(lines)


def validate_slides_before_render(
    slides: list[dict[str, Any]],
    *,
    platform: str = "douyin",
    strict: bool = False,
    brief: dict[str, Any] | None = None,
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
                hero = str(s.get("feature_label") or s.get("heading") or "")
                for j, line in enumerate(lines):
                    if len(line) < SUBTITLE_MIN_CHARS:
                        warnings.append(f"slide_{i}_subtitle_{j}_too_short")
                    if len(line) > SUBTITLE_MAX_CHARS:
                        warnings.append(f"slide_{i}_subtitle_{j}_too_long")
                    if hero and line == hero:
                        warnings.append(f"slide_{i}_subtitle_dup_hero")

            vt = str(s.get("viz_type") or "none")
            if vt not in _VIZ_TYPES:
                errors.append(f"slide_{i}_invalid_viz:{vt}")

            if vt == "line" and len(s.get("chart_series") or []) < 3:
                errors.append(f"slide_{i}_line_without_series")

            if platform == "xhs":
                mp = s.get("motion_params") or {}
                if int(mp.get("captionBottomPx") or 400) < 360:
                    warnings.append(f"slide_{i}_xhs_caption_too_low")
                layout = str(s.get("mid_info_layout") or "")
                if layout == "steps" and len(lines) > 2:
                    warnings.append(f"slide_{i}_xhs_steps_may_overlap_caption")

            coll = check_slide_layout_collision(s)
            if not coll.get("ok"):
                warnings.append(f"slide_{i}_layout_collision:{','.join(coll.get('issues') or [])}")

        raw_pages = s.get("_caption_pages_preview")
        if isinstance(raw_pages, list) and raw_pages:
            issues = validate_caption_pages(raw_pages)
            warnings.extend(issues)

    if empty_mid_run >= 2:
        warnings.append("consecutive_empty_mid_content")

    tts_texts = [str(s.get("tts_text") or "") for s in slides if s.get("tts_text")]
    for phrase in find_unsafe_caption_splits(tts_texts):
        warnings.append(f"unsafe_tts_split:{phrase}")

    banned = validate_slides_tts_copy(slides)
    if banned:
        errors.extend(banned)

    viz_non_none = sum(
        1 for s in slides if _is_content_slide(s) and str(s.get("viz_type") or "none") != "none"
    )
    content_n = sum(1 for s in slides if _is_content_slide(s))
    fk = str((brief or {}).get("feed_kind") or "").lower()
    if fk in ("github", "github_daily", "daily_github") and content_n and viz_non_none < 1:
        stat_in_cards = any(
            "star" in str(x).lower() or "⭐" in str(x) or "火" in str(x) or "热" in str(x)
            for s in slides
            if _is_content_slide(s)
            for x in (s.get("summary_lines") or [])
        )
        has_mid_cards = any(
            len([str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]) >= 2
            for s in slides
            if _is_content_slide(s)
        )
        if not stat_in_cards and not has_mid_cards:
            errors.append("github_viz_required")

    if platform == "xhs":
        modes = {str(s.get("caption_mode") or "") for s in slides}
        if "editorial" not in modes:
            errors.append("xhs_requires_editorial_caption")
        for s in slides:
            if str(s.get("type")) == "content_card" and (s.get("visual_design") or {}).get(
                "broadcast_frame"
            ):
                errors.append("xhs_content_broadcast_frame")

    if platform == "xhs":
        for s in slides:
            if str(s.get("type")) == "cta_card" and not s.get("suppress_bottom_caption"):
                warnings.append("cta_should_suppress_bottom_caption")

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
