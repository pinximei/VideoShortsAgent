"""中部 summary / 信息面板与 TTS 句级时间轴对齐。"""
from __future__ import annotations

import re
from typing import Any


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def compute_summary_reveal_frames(
    summary_lines: list[str],
    sentences: list[dict[str, Any]],
    *,
    fps: int = 30,
    default_stagger: int = 18,
) -> list[int]:
    """
    为每条 summary_line 计算入场帧（匹配口播句 start，否则按句序递增）。
    """
    lines = [str(x).strip() for x in (summary_lines or []) if str(x).strip()]
    if not lines:
        return []

    sents = [
        {"text": str(s.get("text") or ""), "start": float(s.get("start", 0))}
        for s in (sentences or [])
        if str(s.get("text") or "").strip()
    ]

    frames: list[int] = []
    used: set[int] = set()

    for i, line in enumerate(lines):
        key = _norm(line)[:8]
        best_frame = i * default_stagger
        for j, sent in enumerate(sents):
            if j in used:
                continue
            st = _norm(sent["text"])
            if key and (key in st or st[:6] in _norm(line)):
                best_frame = int(sent["start"] * fps)
                used.add(j)
                break
        else:
            if i < len(sents):
                best_frame = int(sents[i]["start"] * fps)
                used.add(i)
        frames.append(max(0, best_frame))

    return frames


def compute_panel_reveal_frame(
    sentences: list[dict[str, Any]],
    *,
    fps: int = 30,
    offset_frames: int = 6,
) -> int:
    """信息面板（steps/compare）在第二句口播附近出现。"""
    sents = sorted(
        [float(s.get("start", 0)) for s in (sentences or []) if str(s.get("text") or "").strip()]
    )
    if len(sents) >= 2:
        return max(0, int(sents[1] * fps) + offset_frames)
    if sents:
        return max(0, int(sents[0] * fps) + offset_frames + 12)
    return offset_frames
