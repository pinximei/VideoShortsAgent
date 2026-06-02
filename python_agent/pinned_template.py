"""抖音 GitHub Daily 固定模板常量（与 templates/pinned_douyin_github_daily_v1.json 对齐）。"""
from __future__ import annotations

PINNED_DOUYIN_TEMPLATE_ID = "douyin_github_daily_v1"
DOUYIN_OPENING_BURST_FRAMES = 84
DOUYIN_MAX_HOOK_BEATS = 2
DOUYIN_SUBTITLE_MIN = 3
DOUYIN_SUBTITLE_MAX = 4

GENERIC_HERO_TITLES = frozenset(
    {
        "核心亮点",
        "核心能力",
        "一步上手",
        "这个仓库",
        "开源神器",
        "值得收藏",
        "解决痛点",
        "马上能用",
    }
)

GENERIC_HERO_FALLBACK = "开源神器"
