"""句内词级时间轴：Edge TTS WordBoundary 或按字数比例估算。"""
from __future__ import annotations

import re
from typing import Any

_CJK = re.compile(r"[\u4e00-\u9fff]")
_WORD = re.compile(
    r"[A-Za-z][A-Za-z0-9_.-]*|\d+(?:\.\d+)?(?:%|万|千|k|K)?|[\u4e00-\u9fff]",
)


def tokenize_spoken_text(text: str) -> list[str]:
    t = (text or "").strip()
    if not t:
        return []
    return [m.group(0) for m in _WORD.finditer(t)]


def estimate_word_timings(
    text: str,
    start_sec: float,
    end_sec: float,
) -> list[dict[str, Any]]:
    """无 WordBoundary 时按 token 权重分配时长。"""
    tokens = tokenize_spoken_text(text)
    if not tokens:
        return []
    dur = max(0.2, end_sec - start_sec)
    weights = []
    for tok in tokens:
        w = max(1, len(tok))
        if _CJK.search(tok):
            w = max(2, w)
        weights.append(w)
    total = sum(weights) or 1
    t0 = start_sec
    out: list[dict[str, Any]] = []
    for tok, w in zip(tokens, weights):
        seg = dur * (w / total)
        out.append({"text": tok, "start": round(t0, 3), "end": round(t0 + seg, 3)})
        t0 += seg
    if out:
        out[-1]["end"] = round(end_sec, 3)
    return out


def align_words_to_sentence(
    sentence: dict[str, Any],
    *,
    prefer_estimated: bool = False,
) -> list[dict[str, Any]]:
    """合并 sentence 上的 words 字段或估算。"""
    start = float(sentence.get("start", 0))
    end = float(sentence.get("end", start + 0.5))
    text = str(sentence.get("text") or "")
    raw = sentence.get("words")
    if raw and isinstance(raw, list) and not prefer_estimated:
        out = []
        for w in raw:
            if not isinstance(w, dict):
                continue
            wt = str(w.get("text") or "")
            if not wt:
                continue
            ws = float(w.get("start", 0))
            we = float(w.get("end", ws + 0.1))
            if we <= ws and ws < 1000:
                we = ws + 0.12
            if ws > 100:
                ws, we = ws / 1000.0, we / 1000.0
            out.append({"text": wt, "start": round(ws, 3), "end": round(we, 3)})
        if out:
            if out[0]["start"] < start - 0.01:
                for o in out:
                    o["start"] = round(start + (o["start"] - out[0]["start"]), 3)
                    o["end"] = round(start + (o["end"] - out[0]["start"]), 3)
            return out
    return estimate_word_timings(text, start, end)


def words_to_caption_tokens(
    sentence: dict[str, Any],
    *,
    buffer_ms: int = 0,
) -> list[dict[str, int | str]]:
    words = align_words_to_sentence(sentence)
    tokens: list[dict[str, int | str]] = []
    for w in words:
        from_ms = max(0, int(float(w["start"]) * 1000) - buffer_ms)
        to_ms = int(float(w["end"]) * 1000) + buffer_ms
        piece = str(w["text"])
        if tokens and not piece.startswith(" "):
            prev = str(tokens[-1]["text"])
            # 中文逐字高亮不加空格；仅拉丁/数字词之间保留间隔
            if not _CJK.search(piece) and not _CJK.search(prev):
                piece = f" {piece}" if not prev.endswith(" ") else piece
        tokens.append({"text": piece, "fromMs": from_ms, "toMs": max(from_ms + 60, to_ms)})
    return tokens
