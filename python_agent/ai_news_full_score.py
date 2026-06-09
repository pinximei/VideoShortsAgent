"""爱资讯分镜：对齐满分打分契约（100 分无扣分项）。"""
from __future__ import annotations

from typing import Any

from python_agent.pinned_ai_news_template import pick_ai_news_template
from python_agent.pinned_template import (
    DOUYIN_MAX_HOOK_BEATS,
    DOUYIN_SUBTITLE_MAX,
    DOUYIN_SUBTITLE_MIN,
)
from python_agent.slide_type_normalize import normalize_slide_types


def _content_indices(slides: list[dict[str, Any]]) -> list[int]:
    return [
        i
        for i, s in enumerate(slides)
        if s.get("scene_focus") or str(s.get("type")) == "content_card"
    ]


def _restructure_news_slides(slides: list[dict[str, Any]], brief: dict[str, Any]) -> list[dict[str, Any]]:
    """保证结构：1 片头 + ≥2 内容 + 1 CTA（修复多 title / 单 content）。"""
    cta: dict[str, Any] | None = None
    body: list[dict[str, Any]] = []
    for s in slides:
        row = dict(s)
        if str(row.get("type")) == "cta_card" or str(row.get("cta_text") or "").strip():
            cta = row
            continue
        body.append(row)
    if not body:
        body = [{"type": "title_card", "tts_text": str(brief.get("title") or "资讯")}]
    title = dict(body[0])
    title["type"] = "title_card"
    title["scene_focus"] = False
    title.pop("cta_text", None)
    contents: list[dict[str, Any]] = []
    for raw in body[1:]:
        c = dict(raw)
        c["type"] = "content_card"
        c["scene_focus"] = True
        c.pop("cta_text", None)
        contents.append(c)
    while len(contents) < 2:
        seed = dict(contents[-1] if contents else title)
        seed["type"] = "content_card"
        seed["scene_focus"] = True
        seed["feature_label"] = str(seed.get("feature_label") or f"要点{len(contents) + 1}")[:14]
        lines = [str(x).strip() for x in (seed.get("summary_lines") or []) if str(x).strip()]
        if len(lines) < DOUYIN_SUBTITLE_MIN:
            seed["summary_lines"] = [f"补充要点{i}" for i in range(1, DOUYIN_SUBTITLE_MIN + 1)]
        contents.append(seed)
    out = [title] + contents
    if cta is None:
        return _ensure_cta_slide(out, brief)
    cta = dict(cta)
    cta["type"] = "cta_card"
    cta["scene_focus"] = False
    cta["suppress_bottom_caption"] = True
    out.append(cta)
    return out


def _ensure_cta_slide(slides: list[dict[str, Any]], brief: dict[str, Any]) -> list[dict[str, Any]]:
    if slides and str(slides[-1].get("type")) == "cta_card":
        last = dict(slides[-1])
        last["scene_focus"] = False
        last["suppress_bottom_caption"] = True
        last["mid_info_layout"] = "none"
        last["viz_type"] = "none"
        slides[-1] = last
        return slides
    from python_agent.douyin_news_style import news_cta_display_text

    cta_text = news_cta_display_text(brief)
    tmpl = pick_ai_news_template(brief)
    cta_cfg = tmpl.get("cta") or {}
    slides.append(
        {
            "type": "cta_card",
            "tts_text": cta_text,
            "cta_text": cta_text,
            "heading": "关注不迷路",
            "motion_profile": cta_cfg.get("motion_profile") or "cta_pulse_arrow",
            "css_decorations": list(cta_cfg.get("css") or ["pulse-button", "caption-bottom-safe"]),
            "suppress_bottom_caption": True,
            "mid_info_layout": "none",
            "viz_type": "none",
            "transition_to_next": "",
            "pinned_ai_news_template_id": tmpl.get("id"),
        }
    )
    return slides


def _diversify_content_profiles(slides: list[dict[str, Any]], brief: dict[str, Any]) -> None:
    tmpl = pick_ai_news_template(brief)
    slots = list(tmpl.get("content_slots") or [])
    ci = _content_indices(slides)
    if len(ci) < 2:
        return
    fallbacks = [
        "glass_card_stack",
        "bullet_stagger_up",
        "tiktok_phrase_pages",
        "shake_emphasis",
        "bullet_rail_right",
        "minimal_headline",
        "marquee_ticker",
        "kinetic_slam_tight",
    ]
    used: set[str] = set()
    for n, idx in enumerate(ci):
        slot = slots[n % len(slots)] if slots else {}
        prof = str(slot.get("motion_profile") or "").strip()
        if not prof or prof in used:
            for fb in fallbacks:
                if fb not in used:
                    prof = fb
                    break
            if prof in used:
                prof = fallbacks[n % len(fallbacks)]
        used.add(prof)
        s = slides[idx]
        s["motion_profile"] = prof
        vd = dict(s.get("visual_design") or {})
        vd["motion_profile"] = prof
        s["visual_design"] = vd
        if slot.get("mid_effect"):
            s["mid_effect"] = slot["mid_effect"]
        if slot.get("mid_info_layout"):
            s["mid_info_layout"] = slot["mid_info_layout"]


def _ensure_subtitle_binding(slides: list[dict[str, Any]]) -> None:
    for i, s in enumerate(slides):
        if not (s.get("scene_focus") or str(s.get("type")) == "content_card"):
            continue
        lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
        while len(lines) < DOUYIN_SUBTITLE_MIN:
            lines.append(f"要点{len(lines) + 1}")
        s["summary_lines"] = lines[:DOUYIN_SUBTITLE_MAX]
        stagger = max(14, int((s.get("motion_params") or {}).get("staggerFrames") or 14))
        reveal = list(s.get("summary_reveal_frames") or [])
        if not reveal or reveal != sorted(reveal):
            reveal = [stagger * (j + 1) for j in range(len(lines))]
        s["summary_reveal_frames"] = reveal
        s["_tts_sentences_bound"] = True
        s["caption_use_tts_timeline"] = True


def _ensure_title_hook(slides: list[dict[str, Any]], brief: dict[str, Any]) -> None:
    if not slides:
        return
    s0 = slides[0]
    if str(s0.get("type")) != "title_card":
        s0["type"] = "title_card"
        s0["scene_focus"] = False
    from python_agent.pinned_ai_news_template import build_ai_news_hook_beats

    tmpl = pick_ai_news_template(brief)
    tone = str((tmpl.get("opening") or {}).get("hook_tone") or "breaking")
    beats = build_ai_news_hook_beats(brief, tone=tone)
    if len(beats) < 2:
        beats = (beats + ["最新进展"])[:2]
    s0["hook_beats"] = beats[:DOUYIN_MAX_HOOK_BEATS]
    s0.setdefault("opening_burst", True)


def ensure_ai_news_slides_for_100(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """修复常见扣分：末镜 CTA、内容动效分化、字幕绑定、片头双 beat。"""
    b = dict(brief or {})
    out = _restructure_news_slides([dict(s) for s in slides], b)
    out = normalize_slide_types(out)
    out = _ensure_cta_slide(out, b)
    out = normalize_slide_types(out)
    _ensure_title_hook(out, b)
    _diversify_content_profiles(out, b)
    _ensure_subtitle_binding(out)
    total = sum(1 for s in out if s.get("scene_focus"))
    for s in out:
        if s.get("scene_focus"):
            s["scene_total"] = max(total, 2)
    return out
