"""成片节奏：给 Remotion 动效留足尾帧，避免切镜过赶。"""
from __future__ import annotations

from typing import Any

# 单镜 TTS 结束后再保留的画面时间（让 spring / 打字机播完）
ANIMATION_TAIL_TITLE_SEC = 1.2
ANIMATION_TAIL_CONTENT_SEC = 1.6
ANIMATION_TAIL_CTA_SEC = 1.0

FREEZE_PAD_SEC = 0.65
SEGMENT_TAIL_PAD_SEC = 0.5
MIN_CONTENT_SLIDE_SEC = 4.2
MIN_TITLE_SLIDE_SEC = 4.2

# 每 content_card 最多拆成几镜（原 3~5 镜过碎）
MAX_SCENES_PER_CONTENT_CARD = 2

# 片段拼接转场（略短，把时长留给单镜内容）
XFADE_DURATION_SEC = 0.58
MONTAGE_TRANSITION_FRAMES = 14


def _slide_kind(slide: dict[str, Any]) -> str:
    st = str(slide.get("type") or "content_card")
    if st == "title_card":
        return "title"
    if st == "cta_card":
        return "cta"
    return "content"


def animation_tail_seconds(slide: dict[str, Any]) -> float:
    kind = _slide_kind(slide)
    if kind == "title":
        return ANIMATION_TAIL_TITLE_SEC
    if kind == "cta":
        return ANIMATION_TAIL_CTA_SEC
    return ANIMATION_TAIL_CONTENT_SEC


def visual_duration_seconds(tts_duration_sec: float, slide: dict[str, Any]) -> float:
    """Remotion 渲染用时长 ≥ TTS，避免动效被掐断。"""
    tts = max(0.5, float(tts_duration_sec))
    tail = animation_tail_seconds(slide)
    minimum = MIN_TITLE_SLIDE_SEC if _slide_kind(slide) == "title" else MIN_CONTENT_SLIDE_SEC
    if _slide_kind(slide) == "content" and not slide.get("scene_focus"):
        minimum = MIN_CONTENT_SLIDE_SEC * 0.85
    return max(minimum, tts + tail + FREEZE_PAD_SEC)


def slide_duration_frames(tts_duration_sec: float, slide: dict[str, Any], *, fps: int = 30) -> int:
    return max(1, int(visual_duration_seconds(tts_duration_sec, slide) * fps))
