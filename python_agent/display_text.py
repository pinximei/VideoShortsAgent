"""屏显与底栏字幕：按语义整句/分句切分，禁止半个词或半句话拆到两页。"""
from __future__ import annotations

import re
from typing import Any

# 底栏单行：抖音略短但仍要完整语义单位（≥6 字优先）
CAPTION_LINE_MAX_CHARS = 22
CAPTION_LINE_MAX_CHARS_DOUYIN = 18
TIKTOK_PHRASE_MAX_CHARS = 18
TIKTOK_PHRASE_MIN_CHARS = 6
HEADING_MAX_CHARS = 28
HEADING_MAX_CHARS_LEGACY = 14
BULLET_MAX_CHARS = 36
BULLET_MAX_COUNT = 5
HOOK_MAX_CHARS = 22

_CLAUSE_END = re.compile(r"[。！？；\n]")
_SOFT_BREAK = re.compile(r"[，,、]")
# 不可从中间切断：英文词、GitHub、数字+% 等
_PROTECTED_SPAN = re.compile(
    r"(?:GitHub|Open\s*Source|API|AI|LLM|Star|Stars|"
    r"\d+(?:\.\d+)?(?:%|万|千|k|K)?|"
    r"[A-Za-z][A-Za-z0-9_.-]{1,24})",
    re.I,
)


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _merge_orphan_fragments(phrases: list[str], *, min_len: int = 4) -> list[str]:
    """把过短碎片并到上一段，避免「一个词拆两页」。"""
    if not phrases:
        return []
    out: list[str] = []
    for p in phrases:
        p = _plain(p)
        if not p:
            continue
        if out and len(p) < min_len:
            out[-1] = _plain(out[-1] + p)
        elif out and len(out[-1]) < min_len:
            out[-1] = _plain(out[-1] + p)
        else:
            out.append(p)
    return out


def _protected_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _PROTECTED_SPAN.finditer(text)]


def _cut_inside_protected(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(a < pos < b for a, b in spans)


def _split_long_at_boundary(clause: str, max_chars: int) -> list[str]:
    """超长分句：优先逗号，再在非保护区内找切点，禁止硬截半词。"""
    if len(clause) <= max_chars:
        return [clause]
    spans = _protected_spans(clause)
    parts = [p.strip() for p in _SOFT_BREAK.split(clause) if p.strip()]
    if len(parts) > 1:
        out: list[str] = []
        buf = ""
        for part in parts:
            candidate = _plain(buf + part) if buf else part
            if len(candidate) <= max_chars:
                buf = candidate
            else:
                if buf:
                    out.append(buf)
                if len(part) <= max_chars:
                    buf = part
                else:
                    out.extend(_split_long_at_boundary(part, max_chars))
                    buf = ""
        if buf:
            out.append(buf)
        return _merge_orphan_fragments(out, min_len=TIKTOK_PHRASE_MIN_CHARS // 2)

    # 无逗号：从 max_chars 往前找安全切点（2~4 字步进）
    out = []
    rest = clause
    while len(rest) > max_chars:
        cut = max_chars
        while cut > max_chars // 2 and _cut_inside_protected(cut, spans):
            cut -= 1
        if cut <= max_chars // 2:
            cut = max_chars
        piece = rest[:cut].strip()
        if piece:
            out.append(piece)
        rest = rest[cut:].strip()
        spans = _protected_spans(rest)
    if rest:
        out.append(rest)
    return _merge_orphan_fragments(out, min_len=TIKTOK_PHRASE_MIN_CHARS // 2)


def find_unsafe_caption_splits(phrases: list[str]) -> list[str]:
    """检测疑似半词/半句拆页（用于门禁）。"""
    issues: list[str] = []
    for i, p in enumerate(phrases):
        t = _plain(p)
        if len(t) < 4 and i + 1 < len(phrases):
            issues.append(f"orphan_fragment:{t!r}")
        if i + 1 < len(phrases):
            nxt = _plain(phrases[i + 1])
            if len(t) + len(nxt) <= TIKTOK_PHRASE_MAX_CHARS + 4:
                if not _CLAUSE_END.search(t) and not _SOFT_BREAK.search(t):
                    if t[-1:].isalnum() and nxt[:1].isalnum():
                        issues.append(f"merge_candidate:{t}|{nxt}")
    return issues


def split_spoken_clauses(text: str, *, max_chars: int = CAPTION_LINE_MAX_CHARS) -> list[str]:
    """
    只按句号/问号/叹号/分号切大句；超长分句才按逗号拆，禁止固定字数硬切词。
    """
    t = _plain(text)
    if not t:
        return []
    if len(t) <= max_chars:
        return [t]

    clauses = [c.strip() for c in _CLAUSE_END.split(t) if c.strip()]
    if not clauses:
        clauses = [t]

    out: list[str] = []
    for clause in clauses:
        if len(clause) <= max_chars:
            out.append(clause)
            continue
        out.extend(_split_long_at_boundary(clause, max_chars))

    return _merge_orphan_fragments(out, min_len=TIKTOK_PHRASE_MIN_CHARS // 2)


def split_spoken_phrases(text: str, *, max_chars: int = CAPTION_LINE_MAX_CHARS) -> list[str]:
    """口播/底栏同步：语义分句（兼容旧调用）。"""
    return split_spoken_clauses(text, max_chars=max_chars)


def split_tiktok_caption_sentences(
    sentences: list[dict[str, Any]],
    *,
    max_chars: int = TIKTOK_PHRASE_MAX_CHARS,
) -> list[dict[str, Any]]:
    """抖音底栏：每页一条完整语义短语，按 TTS 时间轴比例切分。"""
    out: list[dict[str, Any]] = []
    for seg in sentences or []:
        text = _plain(str(seg.get("text", "") or ""))
        if not text:
            continue
        start = float(seg.get("start", 0))
        end = float(seg.get("end", start + 1))
        dur = max(0.35, end - start)
        phrases = split_spoken_clauses(text, max_chars=max_chars)
        phrases = _merge_orphan_fragments(phrases, min_len=4)
        if not phrases:
            continue
        if len(phrases) == 1:
            out.append({"text": phrases[0], "start": start, "end": end})
            continue
        total = sum(max(1, len(p)) for p in phrases)
        t0 = start
        for i, p in enumerate(phrases):
            frac = max(1, len(p)) / total
            t1 = end if i == len(phrases) - 1 else t0 + dur * frac
            out.append({"text": p, "start": round(t0, 3), "end": round(t1, 3)})
            t0 = t1
    return out


def split_caption_sentences(
    sentences: list[dict[str, Any]],
    *,
    max_chars: int | None = None,
) -> list[dict[str, Any]]:
    cap = max_chars or CAPTION_LINE_MAX_CHARS
    return split_tiktok_caption_sentences(sentences, max_chars=cap)


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


def fit_slide_for_display(slide: dict[str, Any], *, legacy_compact: bool = False) -> dict[str, Any]:
    s = dict(slide)
    use_legacy = legacy_compact or not (
        s.get("github_daily_style_id") or s.get("motion_profile")
    )
    hmax = HEADING_MAX_CHARS_LEGACY if use_legacy else HEADING_MAX_CHARS
    if s.get("heading"):
        s["heading"] = fit_heading(str(s["heading"]), max_chars=hmax)
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


def caption_font_size_for_text(text: str, *, base: int = 52, min_size: int = 30) -> int:
    n = len(_plain(text))
    if n <= 8:
        return base
    if n <= 12:
        return 46
    if n <= 16:
        return 40
    return min_size
