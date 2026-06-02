"""中部 summary / 信息面板与 TTS 句级时间轴对齐。"""
from __future__ import annotations

import re
from typing import Any


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def _overlap_ratio(a: str, b: str) -> float:
    ka, kb = _norm(a), _norm(b)
    if not ka or not kb:
        return 0.0
    if ka == kb or ka in kb or kb in ka:
        return 1.0
    common = sum(1 for ch in ka if ch in kb)
    return common / max(len(ka), 1)


def _best_sentence_index(line: str, sents: list[dict[str, Any]]) -> int:
    best_i, best_score = 0, 0.0
    for i, s in enumerate(sents):
        score = _overlap_ratio(line, str(s.get("text") or ""))
        if score > best_score:
            best_score, best_i = score, i
    return best_i


def compute_summary_reveal_frames(
    summary_lines: list[str],
    sentences: list[dict[str, Any]],
    *,
    fps: int = 30,
    default_stagger: int = 40,
) -> list[int]:
    """
    为每条 summary_line 计算入场帧（严格按 1→2→3 顺序，时间单调递增）。
    """
    lines = [str(x).strip() for x in (summary_lines or []) if str(x).strip()]
    if not lines:
        return []

    sents = [
        {"text": str(s.get("text") or ""), "start": float(s.get("start", 0))}
        for s in (sentences or [])
        if str(s.get("text") or "").strip()
    ]

    panel = compute_panel_reveal_frame(sentences, fps=fps, offset_frames=12)
    stagger = max(14, default_stagger // 2)

    frames: list[int] = []
    used_sent: set[int] = set()
    for i, line in enumerate(lines):
        j = _best_sentence_index(line, sents)
        if j in used_sent and len(sents) > 1:
            j = min(i, len(sents) - 1)
        used_sent.add(j)
        t = int(sents[j]["start"] * fps) if sents else panel + i * stagger
        if i == 0:
            frames.append(max(0, t))
        else:
            frames.append(max(frames[i - 1] + stagger, t))

    return frames


def compute_panel_reveal_frame(
    sentences: list[dict[str, Any]],
    *,
    fps: int = 30,
    offset_frames: int = 18,
) -> int:
    """信息面板第一张子标题入场帧（紧跟首句口播后）。"""
    sents = sorted(
        [float(s.get("start", 0)) for s in (sentences or []) if str(s.get("text") or "").strip()]
    )
    if len(sents) >= 1:
        return max(0, int(sents[0] * fps) + offset_frames)
    return offset_frames
