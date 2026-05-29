"""VSA 能力目录：特效、样式、场景，供中间层 LLM 与连接器统一引用。"""
from .registry import (
    effects_catalog,
    llm_capabilities_section,
    merge_render_effects,
    platform_video_defaults,
    save_catalog_snapshot,
)

__all__ = [
    "effects_catalog",
    "llm_capabilities_section",
    "merge_render_effects",
    "platform_video_defaults",
    "save_catalog_snapshot",
]
