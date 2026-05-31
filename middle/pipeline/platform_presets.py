"""各发布平台预设（中间层统一维护）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PlatformPreset:
    id: str
    label: str
    content_kind: str  # video | article
    width: int = 0
    height: int = 0
    max_seconds: float = 0.0
    voice: str = ""
    effects: dict[str, Any] = field(default_factory=dict)
    publish_file: str = ""


PLATFORM_PRESETS: dict[str, PlatformPreset] = {
    "douyin": PlatformPreset(
        id="douyin",
        label="抖音",
        content_kind="video",
        width=1080,
        height=1920,
        max_seconds=45.0,
        voice="zh-CN-YunyangNeural",
        effects={
            "preset": "活力",
            "use_remotion": True,
            "caption_style": "spring",
            "transition": "slideup",
            "transition_duration": 0.22,
            "gradient": False,
            "intro_card": True,
            "outro_card": True,
        },
    ),
    "xhs": PlatformPreset(
        id="xhs",
        label="小红书",
        content_kind="video",
        width=1080,
        height=1920,
        max_seconds=55.0,
        voice="zh-CN-XiaoxiaoNeural",
        effects={
            "preset": "情感",
            "use_remotion": True,
            "caption_style": "fade",
            "gradient": False,
            "gradient_colors": ["#FF9A9E", "#FECFEF"],
            "transition": "dissolve",
            "transition_duration": 0.25,
            "intro_card": True,
            "outro_card": True,
        },
    ),
    "toutiao": PlatformPreset(id="toutiao", label="今日头条", content_kind="article", publish_file="toutiao_micro.txt"),
    "douban": PlatformPreset(id="douban", label="豆瓣", content_kind="article", publish_file="douban_note.txt"),
}

DEFAULT_VIDEO_PLATFORMS = ("douyin", "xhs")
DEFAULT_ARTICLE_PLATFORMS = ("toutiao", "douban")


def get_platform_preset(platform_id: str) -> PlatformPreset:
    key = (platform_id or "").strip().lower()
    if key not in PLATFORM_PRESETS:
        raise ValueError(f"未知平台: {platform_id}")
    return PLATFORM_PRESETS[key]


def is_video_platform(platform_id: str) -> bool:
    return get_platform_preset(platform_id).content_kind == "video"


def video_platforms(ids: list[str] | None = None) -> list[PlatformPreset]:
    wanted = ids or list(DEFAULT_VIDEO_PLATFORMS)
    return [get_platform_preset(p) for p in wanted if is_video_platform(p)]
