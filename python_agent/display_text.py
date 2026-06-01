"""屏显与底栏字幕：单行、跟口播时间轴；标题/要点短截断；tts_text 不裁。"""
from __future__ import annotations

import re
from typing import Any

# 底栏单行安全字数（与 CaptionOverlay 动态字号对齐）
CAPTION_LINE_MAX_CHARS = 12
CAPTION_LINE_MAX_CHARS_DOUYIN = 10
HEADING_MAX_CHARS = 14
BULLET_MAX_CHARS = 20
BULLET_MAX_COUNT = 4
HOOK_MAX_CHARS = 16


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _split_fixed_chunks(text: str, *, max_chars: int) -> list[str]:
    """无标点时按字数切分为单行片段。"""
    t = _plain(text)
    if not t:
        return []
    if len(t) <= max_chars:
        return [t]
    out: list[str] = []
    i = 0
    while i < len(t):
        chunk = t[i : i + max_chars]
        if len(chunk) < max_chars:
            out.append(chunk)
            break
        break_at = -1
        for p in "，,。！？；;、 ":
            pos = chunk.rfind(p)
            if pos > max_chars // 3:
                break_at = pos + 1
                break
        if break_at > 0:
            out.append(chunk[:break_at].strip())
            i += break_at
        else:
            out.append(chunk)
            i += max_chars
    return [x for x in out if x]


def split_spoken_phrases(text: str, *, max_chars: int = CAPTION_LINE_MAX_CHARS) -> list[str]:
    """拆成口播/底栏同步用的单行字幕（每段对应一次 TTS + 一屏一行）。"""
    t = _plain(text)
    if not t:
        return []
    parts = re.split(r"[。！？；\n]+", t)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        parts = [t]
    out: list[str] = []
    for part in parts:
        if len(part) <= max_chars:
            out.append(part)
            continue
        sub = re.split(r"[，,、]+", part)
        sub = [s.strip() for s in sub if s.strip()]
        if len(sub) > 1:
            for s in sub:
                out.extend(
                    _split_fixed_chunks(s, max_chars=max_chars)
                    if len(s) > max_chars
                    else [s]
                )
        else:
            out.extend(_split_fixed_chunks(part, max_chars=max_chars))
    return out if out else [t]


def fit_heading(text: str, *, max_chars: int = HEADING_MAX_CHARS) -> str:
    t = _plain(text)
    if len(t) <= max_chars:
        return t
    return t[: max(1, max_chars - 1)] + "…"


def fit_hook(text: str) -> str:
    return fit_heading(text, max_chars=HOOK_MAX_CHARS)


def fit_bullets(bullets: list[Any], *, max_items: int = BULLET_MAX_COUNT) -> list[str]:
    out: list[str] = []
    for b in bullets[:max_items]:
        if isinstance(b, dict):
            raw = str(b.get("text", "") or "")
        else:
            raw = str(b)
        t = _plain(raw)
        if not t:
            continue
        if len(t) > BULLET_MAX_CHARS:
            t = t[: BULLET_MAX_CHARS - 1] + "…"
        out.append(t)
    return out


def fit_slide_for_display(slide: dict[str, Any]) -> dict[str, Any]:
    """就地规范化单镜屏显字段（不改 tts_text）。"""
    s = dict(slide)
    if s.get("heading"):
        s["heading"] = fit_heading(str(s["heading"]))
    if s.get("hook_text"):
        s["hook_text"] = fit_hook(str(s["hook_text"]))
    if s.get("subheading"):
        s["subheading"] = fit_heading(str(s["subheading"]), max_chars=18)
    raw = s.get("bullets") or []
    fitted = fit_bullets(raw if isinstance(raw, list) else [])
    new_bullets: list[Any] = []
    for i, text in enumerate(fitted):
        if i < len(raw) and isinstance(raw[i], dict):
            b = dict(raw[i])
            b["text"] = text
            new_bullets.append(b)
        else:
            new_bullets.append(text)
    s["bullets"] = new_bullets
    return s


def split_caption_sentences(
    sentences: list[dict[str, Any]],
    *,
    max_chars: int | None = None,
) -> list[dict[str, Any]]:
    """长句按时轴均分为多段单行字幕，与口播进度对齐（不含换行符）。"""
    cap = max_chars or CAPTION_LINE_MAX_CHARS
    out: list[dict[str, Any]] = []
    for seg in sentences or []:
        text = _plain(str(seg.get("text", "") or ""))
        if not text:
            continue
        start = float(seg.get("start", 0))
        end = float(seg.get("end", start + 1))
        dur = max(0.25, end - start)
        phrases = split_spoken_phrases(text, max_chars=cap)
        if len(phrases) <= 1:
            out.append({"text": phrases[0] if phrases else text, "start": start, "end": end})
            continue
        total = sum(max(1, len(p)) for p in phrases)
        t0 = start
        for i, p in enumerate(phrases):
            frac = max(1, len(p)) / total
            t1 = end if i == len(phrases) - 1 else t0 + dur * frac
            out.append({"text": p, "start": round(t0, 3), "end": round(t1, 3)})
            t0 = t1
    return out


def caption_font_size_for_text(text: str, *, base: int = 52, min_size: int = 30) -> int:
    """单行底栏字号（字越多越小，保证一行内显示）。"""
    n = len(_plain(text))
    if n <= 8:
        return base
    if n <= 12:
        return 46
    if n <= 16:
        return 40
    return min_size
