"""底栏字幕时间轴：与 TTS 句级时间对齐，避免 Remotion 二次分页。"""
from __future__ import annotations

from typing import Any

from python_agent.display_text import (
    CAPTION_LINE_MAX_CHARS,
    CAPTION_LINE_MAX_CHARS_DOUYIN,
    TIKTOK_PHRASE_MAX_CHARS,
    find_unsafe_caption_splits,
    split_tiktok_caption_sentences,
)

CAPTION_BUFFER_MS = 50
XHS_CAPTION_BUFFER_MS = 80


def sentences_to_caption_pages(
    sentences: list[dict[str, Any]],
    *,
    buffer_ms: int = CAPTION_BUFFER_MS,
) -> list[dict[str, Any]]:
    """TTS 一句 = 一页（startMs/durationMs/tokens）。"""
    if not sentences:
        return []

    pages: list[dict[str, Any]] = []
    for s in sentences:
        text = str(s.get("text") or "").strip()
        if not text:
            continue
        start_s = float(s.get("start", 0))
        end_s = float(s.get("end", start_s + 0.5))
        start_ms = max(0, int(start_s * 1000) - buffer_ms)
        end_ms = int(end_s * 1000) + buffer_ms
        token_from = int(start_s * 1000)
        token_to = max(token_from + 80, int(end_s * 1000))
        pages.append(
            {
                "text": text,
                "startMs": start_ms,
                "durationMs": max(280, end_ms - start_ms),
                "tokens": [{"text": text, "fromMs": token_from, "toMs": token_to}],
            }
        )

    for i in range(len(pages) - 1):
        next_start = pages[i + 1]["startMs"]
        pages[i]["durationMs"] = max(280, next_start - pages[i]["startMs"])

    if pages:
        last = pages[-1]
        last_end = int(float(sentences[-1].get("end", 0)) * 1000) + buffer_ms
        last["durationMs"] = max(280, last_end - last["startMs"])

    return pages


def prepare_slide_captions(
    raw_sentences: list[dict[str, Any]],
    slide: dict[str, Any],
    *,
    platform: str = "douyin",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    返回 (sentences, caption_pages)。
    默认使用 TTS 时间轴，不再在渲染层按字数重切。
    """
    plat = (platform or slide.get("platform") or "douyin").strip().lower()
    use_tts = slide.get("caption_use_tts_timeline", True)
    cap_mode = slide.get("caption_mode") or ""

    if not raw_sentences:
        return [], []

    if use_tts and cap_mode == "tiktok":
        sentences = [
            {
                "text": str(s.get("text") or "").strip(),
                "start": float(s.get("start", 0)),
                "end": float(s.get("end", 0)),
            }
            for s in raw_sentences
            if str(s.get("text") or "").strip()
        ]
        buf = XHS_CAPTION_BUFFER_MS if plat == "xhs" else CAPTION_BUFFER_MS
        pages = sentences_to_caption_pages(sentences, buffer_ms=buf)
        return sentences, pages

    max_chars = (
        CAPTION_LINE_MAX_CHARS_DOUYIN
        if cap_mode == "tiktok"
        else CAPTION_LINE_MAX_CHARS
    )
    if cap_mode == "tiktok":
        sentences = split_tiktok_caption_sentences(raw_sentences, max_chars=TIKTOK_PHRASE_MAX_CHARS)
    else:
        sentences = split_tiktok_caption_sentences(raw_sentences, max_chars=max_chars)

    buf = XHS_CAPTION_BUFFER_MS if plat == "xhs" else CAPTION_BUFFER_MS
    pages = sentences_to_caption_pages(sentences, buffer_ms=buf)
    return sentences, pages


def caption_pages_for_props(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remotion props 可 JSON 序列化的 captionPages。"""
    out: list[dict[str, Any]] = []
    for p in pages:
        out.append(
            {
                "text": p.get("text", ""),
                "startMs": int(p.get("startMs", 0)),
                "durationMs": int(p.get("durationMs", 500)),
                "tokens": [
                    {
                        "text": t.get("text", ""),
                        "fromMs": int(t.get("fromMs", 0)),
                        "toMs": int(t.get("toMs", 0)),
                    }
                    for t in (p.get("tokens") or [])
                ],
            }
        )
    return out


def validate_caption_pages(pages: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    for i, p in enumerate(pages):
        text = str(p.get("text") or "").strip()
        if len(text) < 4:
            issues.append(f"caption_page_{i}_too_short:{text!r}")
        dur = int(p.get("durationMs") or 0)
        if dur < 200:
            issues.append(f"caption_page_{i}_duration_too_short:{dur}ms")
    issues.extend(find_unsafe_caption_splits([str(p.get("text") or "") for p in pages]))
    return issues
