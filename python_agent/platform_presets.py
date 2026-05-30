"""各发布平台预设：视频渠道 vs 文章渠道分开管理。"""
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
    caption_style: str = ""
    hook_caption_style: str = ""
    body_caption_style: str = ""
    cta_caption_style: str = ""
    hook_transition: str = "fade"
    body_transition: str = "fade"
    effects: dict[str, Any] = field(default_factory=dict)
    publish_file: str = ""  # 文章渠道：publish 目录下文案文件名


PLATFORM_PRESETS: dict[str, PlatformPreset] = {
    "douyin": PlatformPreset(
        id="douyin",
        label="抖音",
        content_kind="video",
        width=1080,
        height=1920,
        max_seconds=45.0,
        voice="zh-CN-YunxiNeural",
        caption_style="spring",
        hook_caption_style="spring",
        body_caption_style="spring",
        cta_caption_style="spring",
        hook_transition="circleopen",
        body_transition="fade",
        effects={
            "use_remotion": True,
            "caption_style": "spring",
            "transition": "fade",
            "transition_duration": 0.22,
            "gradient": False,
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
        caption_style="情感",
        hook_caption_style="情感",
        body_caption_style="情感",
        cta_caption_style="情感",
        hook_transition="dissolve",
        body_transition="dissolve",
        effects={
            "use_remotion": True,
            "caption_style": "fade",
            "transition": "dissolve",
            "transition_duration": 0.25,
            "gradient": True,
            "gradient_colors": ["#FF9A9E", "#FECFEF"],
        },
    ),
    "toutiao": PlatformPreset(
        id="toutiao",
        label="今日头条",
        content_kind="article",
        publish_file="toutiao_micro.txt",
    ),
    "douban": PlatformPreset(
        id="douban",
        label="豆瓣",
        content_kind="article",
        publish_file="douban_note.txt",
    ),
}

# 默认只出视频（与 Pipeline publish_stats.CHANNEL_KIND 一致）
DEFAULT_VIDEO_PLATFORMS: tuple[str, ...] = ("douyin", "xhs")
DEFAULT_ARTICLE_PLATFORMS: tuple[str, ...] = ("toutiao", "douban")


def get_platform_preset(platform_id: str) -> PlatformPreset:
    key = (platform_id or "").strip().lower()
    if key not in PLATFORM_PRESETS:
        raise ValueError(f"未知平台: {platform_id}，可选: {', '.join(PLATFORM_PRESETS)}")
    return PLATFORM_PRESETS[key]


def list_platform_ids() -> list[str]:
    return list(PLATFORM_PRESETS.keys())


def list_video_platform_ids() -> list[str]:
    return [p.id for p in PLATFORM_PRESETS.values() if p.content_kind == "video"]


def list_article_platform_ids() -> list[str]:
    return [p.id for p in PLATFORM_PRESETS.values() if p.content_kind == "article"]


def is_video_platform(platform_id: str) -> bool:
    return get_platform_preset(platform_id).content_kind == "video"
