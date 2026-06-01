"""屏显文案适配竖屏 1080×1920：换行、截断、字幕分句（口播 tts_text 不裁）。"""
from __future__ import annotations

import re
from typing import Any

# 竖屏安全区（与 CaptionOverlay padding 对齐）
CAPTION_MAX_CHARS_PER_LINE = 14
CAPTION_MAX_LINES = 3
HEADING_MAX_CHARS = 14
BULLET_MAX_CHARS = 20
BULLET_MAX_COUNT = 4
HOOK_MAX_CHARS = 16


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def wrap_lines(text: str, *, max_chars: int, max_lines: int) -> str:
    """按字数换行，超出 max_lines 时末行省略号。"""
    t = _plain(text)
    if not t:
        return ""
    lines: list[str] = []
    i = 0
    while i < len(t) and len(lines) < max_lines:
        chunk = t[i : i + max_chars]
        if len(chunk) < max_chars:
            lines.append(chunk)
            break
        # 尽量在标点处断行
        break_at = -1
        for p in "，,。！？；;、":
            pos = chunk.rfind(p)
            if pos > max_chars // 3:
                break_at = pos + 1
                break
        if break_at > 0:
            lines.append(chunk[:break_at].strip())
            i += break_at
        else:
            if len(lines) == max_lines - 1 and i + max_chars < len(t):
                lines.append(chunk[: max(1, max_chars - 1)] + "…")
                break
            lines.append(chunk)
            i += max_chars
    return "\n".join(lines)


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


def split_caption_sentences(sentences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """过长单句拆成多段字幕，避免底栏 nowrap 裁切。"""
    max_chars = CAPTION_MAX_CHARS_PER_LINE * CAPTION_MAX_LINES
    out: list[dict[str, Any]] = []
    for seg in sentences or []:
        text = _plain(str(seg.get("text", "") or ""))
        if not text:
            continue
        start = float(seg.get("start", 0))
        end = float(seg.get("end", start + 1))
        dur = max(0.3, end - start)
        if len(text) <= max_chars:
            out.append({"text": text, "start": start, "end": end})
            continue
        # 按标点或固定长度切分
        parts: list[str] = []
        buf = ""
        for ch in text:
            buf += ch
            if ch in "，,。！？；;、 " and buf.strip():
                parts.append(buf.strip())
                buf = ""
            elif len(buf) >= CAPTION_MAX_CHARS_PER_LINE:
                parts.append(buf)
                buf = ""
        if buf.strip():
            parts.append(buf.strip())
        if not parts:
            parts = [text[:max_chars]]
        step = dur / len(parts)
        t0 = start
        for i, p in enumerate(parts):
            chunk = wrap_lines(p, max_chars=CAPTION_MAX_CHARS_PER_LINE, max_lines=CAPTION_MAX_LINES)
            t1 = end if i == len(parts) - 1 else t0 + step
            out.append({"text": chunk, "start": round(t0, 3), "end": round(t1, 3)})
            t0 = t1
    return out


def caption_font_size_for_text(text: str, *, base: int = 52, min_size: int = 32) -> int:
    """根据字数估算底栏字号。"""
    plain = text.replace("\n", "")
    n = len(plain)
    if n <= 16:
        return base
    if n <= 28:
        return 46
    if n <= 40:
        return 40
    return min_size
