"""TTS 句级时间轴 → 子标题文案与 reveal 帧绑定。"""
from __future__ import annotations

import re
from typing import Any

from python_agent.subtitle_copy import (
    SUBTITLE_MAX_CHARS,
    SUBTITLE_MIN_CHARS,
    _clamp_subtitle,
    _too_similar,
    normalize_slide_mid_copy,
)
from python_agent.summary_timing import (
    compute_panel_reveal_frame,
    compute_summary_reveal_frames,
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def _overlap(a: str, b: str) -> float:
    ka, kb = _norm(a), _norm(b)
    if not ka or not kb:
        return 0.0
    if ka == kb or ka in kb or kb in ka:
        return 1.0
    common = sum(1 for ch in ka if ch in kb)
    return common / max(len(ka), 1)


def _sentences_from_clip(clip: dict[str, Any]) -> list[dict[str, Any]]:
    raw = clip.get("sentences") or []
    out: list[dict[str, Any]] = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        text = str(s.get("text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "text": text,
                "start": float(s.get("start", 0)),
                "end": float(s.get("end", s.get("start", 0))),
            }
        )
    return sorted(out, key=lambda x: x["start"])


def _clauses_from_sentence(text: str) -> list[str]:
    parts: list[str] = []
    for seg in re.split(r"[，,、；;]", text):
        c = _clamp_subtitle(seg)
        if c and len(c) >= SUBTITLE_MIN_CHARS:
            parts.append(c)
    if not parts:
        c = _clamp_subtitle(text)
        if c:
            parts.append(c)
    return parts


def build_summary_lines_from_sentences(
    sentences: list[dict[str, Any]],
    hero: str,
    *,
    min_cards: int = 3,
    max_cards: int = 4,
) -> list[str]:
    """从口播句提取子标题；跳过与 hero 复述的首句。"""
    cards: list[str] = []
    for i, sent in enumerate(sentences):
        text = str(sent.get("text") or "")
        clauses = _clauses_from_sentence(text)
        if i == 0 and _overlap(text, hero) >= 0.55:
            clauses = [c for c in clauses if not _too_similar(c, hero)]
        for c in clauses:
            if _too_similar(c, hero) or any(_too_similar(c, x) for x in cards):
                continue
            cards.append(c)
            if len(cards) >= max_cards:
                return cards
    while len(cards) < min_cards and sentences:
        for sent in sentences:
            c = _clamp_subtitle(str(sent.get("text") or ""))
            if c and not _too_similar(c, hero) and c not in cards:
                cards.append(c[:SUBTITLE_MAX_CHARS])
            if len(cards) >= min_cards:
                break
        break
    return cards[:max_cards]


def bind_slide_tts_timing(
    slide: dict[str, Any],
    clip: dict[str, Any],
    *,
    fps: int = 30,
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    s = dict(slide)
    sentences = _sentences_from_clip(clip)
    if not sentences:
        return s

    hero = str(s.get("feature_label") or s.get("heading") or "").strip()
    lines = [str(x).strip() for x in (s.get("summary_lines") or []) if str(x).strip()]
    if len(lines) < 3:
        lines = build_summary_lines_from_sentences(sentences, hero, min_cards=3, max_cards=4)
    s["summary_lines"] = lines
    s = normalize_slide_mid_copy(s, brief)
    lines = list(s.get("summary_lines") or [])

    stagger = max(14, int((s.get("motion_params") or {}).get("staggerFrames") or 18))
    reveal = compute_summary_reveal_frames(
        lines, sentences, fps=fps, default_stagger=stagger
    )
    s["summary_reveal_frames"] = reveal
    s["panel_reveal_frame"] = compute_panel_reveal_frame(sentences, fps=fps)
    s["_tts_sentences_bound"] = True
    return s


def apply_tts_subtitle_bind(
    slides: list[dict[str, Any]],
    tts_clips: list[dict[str, Any]],
    *,
    platform: str = "douyin",
    brief: dict[str, Any] | None = None,
    fps: int = 30,
) -> list[dict[str, Any]]:
    """TTS 生成后：子标题与 reveal 帧与句级时间轴对齐。"""
    if platform != "douyin":
        return slides
    from python_agent.layout_collision import fix_all_layout_collisions

    out: list[dict[str, Any]] = []
    for i, slide in enumerate(slides):
        s = dict(slide)
        clip = tts_clips[i] if i < len(tts_clips) else {}
        if _is_content(s) and clip:
            s = bind_slide_tts_timing(s, clip, fps=fps, brief=brief)
        elif str(s.get("type")) == "cta_card" and clip:
            sents = _sentences_from_clip(clip)
            peak = 0.0
            for sent in sents:
                t = str(sent.get("text") or "")
                if any(k in t for k in ("试试", "收藏", "关注", "链接", "GitHub")):
                    peak = float(sent.get("start", peak))
                    break
            if not peak and sents:
                peak = float(sents[-1].get("start", 0))
            s["heading_start_frame"] = max(0, int(peak * fps) - 6)
            s["_cta_peak_bound"] = True
        out.append(s)
    return fix_all_layout_collisions(out)


def _is_content(s: dict[str, Any]) -> bool:
    return bool(s.get("scene_focus")) or str(s.get("type")) == "content_card"
