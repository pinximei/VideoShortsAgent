"""Remotion SlidesMontage 与 TTS 时长对齐（与 SlidesMontage.tsx TRANSITION_FRAMES 一致）。"""
from __future__ import annotations

MONTAGE_TRANSITION_FRAMES = 14
FREEZE_PAD_SEC = 0.3


def slide_duration_frames(tts_duration_sec: float, fps: int = 30) -> int:
    """单镜帧数（含末帧冻结延长）。"""
    return max(1, int((float(tts_duration_sec) + FREEZE_PAD_SEC) * fps))


def montage_total_frames(segment_frames: list[int], *, transition_frames: int = MONTAGE_TRANSITION_FRAMES) -> int:
    n = len(segment_frames)
    if n == 0:
        return 1
    total = sum(max(1, f) for f in segment_frames)
    return max(1, total - transition_frames * max(0, n - 1))


def montage_duration_seconds(segment_frames: list[int], fps: int = 30) -> float:
    return montage_total_frames(segment_frames, transition_frames=MONTAGE_TRANSITION_FRAMES) / fps
