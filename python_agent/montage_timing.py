"""Remotion SlidesMontage 与 TTS 时长对齐（与 SlidesMontage.tsx TRANSITION_FRAMES 一致）。"""
from __future__ import annotations

from python_agent.pace_config import (
    MONTAGE_TRANSITION_FRAMES,
    slide_duration_frames as pace_slide_frames,
    visual_duration_seconds,
)

FREEZE_PAD_SEC = 0.65


def slide_duration_frames(
    tts_duration_sec: float,
    slide: dict | None = None,
    *,
    fps: int = 30,
) -> int:
    if slide:
        return pace_slide_frames(tts_duration_sec, slide, fps=fps)
    return max(1, int((float(tts_duration_sec) + FREEZE_PAD_SEC) * fps))


def montage_total_frames(segment_frames: list[int], *, transition_frames: int = MONTAGE_TRANSITION_FRAMES) -> int:
    n = len(segment_frames)
    if n == 0:
        return 1
    total = sum(max(1, f) for f in segment_frames)
    return max(1, total - transition_frames * max(0, n - 1))


def montage_duration_seconds(segment_frames: list[int], fps: int = 30) -> float:
    return montage_total_frames(segment_frames, transition_frames=MONTAGE_TRANSITION_FRAMES) / fps
