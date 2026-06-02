"""抖音内容镜十种排型（L01–L10）分配表。"""
from __future__ import annotations

from typing import Any

# 线条类装饰不与 corner-brackets 同屏（由 reconcile _css_pack 处理）
_LINE_CLASH = frozenset({"glass-card", "scan-lines", "grid-tunnel-bg"})


def css_pack(items: list[str]) -> list[str]:
    out: list[str] = []
    has_corner = "corner-brackets" in items
    for d in items:
        if has_corner and d in _LINE_CLASH:
            continue
        if d not in out:
            out.append(d)
    return out


DOUYIN_CONTENT_LAYOUTS: tuple[dict[str, Any], ...] = (
    {
        "id": "L01_glass_warm",
        "name": "暖色玻璃竖卡",
        "motion_profile": "glass_card_stack",
        "css": css_pack(["soft-purple-gradient", "sparkle-dots", "github-badge"]),
        "stagger_frames": 14,
        "mid_effect": "typewriter",
    },
    {
        "id": "L02_stagger_up",
        "name": "逐条上推竖卡",
        "motion_profile": "bullet_stagger_up",
        "css": css_pack(["sparkle-dots", "text-stroke-yellow", "float-icon"]),
        "stagger_frames": 14,
        "mid_effect": "glow_ring",
    },
    {
        "id": "L03_kinetic_slam",
        "name": "冲击标题+竖卡",
        "motion_profile": "kinetic_slam_tight",
        "css": css_pack(["soft-purple-gradient", "float-icon", "sparkle-dots"]),
        "stagger_frames": 12,
        "mid_effect": "particle_dust",
    },
    {
        "id": "L04_shake_emphasis",
        "name": "强调抖动竖卡",
        "motion_profile": "shake_emphasis",
        "css": css_pack(["sparkle-dots", "github-badge"]),
        "stagger_frames": 16,
        "mid_effect": "glow_ring",
    },
    {
        "id": "L05_glass_star",
        "name": "玻璃+星标数据感",
        "motion_profile": "glass_card_stack",
        "css": css_pack(["sparkle-dots", "odometer-stars"]),
        "stagger_frames": 14,
        "mid_effect": "typewriter",
    },
    {
        "id": "L06_bullet_float",
        "name": "上浮图标竖卡",
        "motion_profile": "bullet_stagger_up",
        "css": css_pack(["float-icon", "sparkle-dots"]),
        "stagger_frames": 13,
        "mid_effect": "glow_scan",
    },
    {
        "id": "L07_kinetic_minimal",
        "name": "极简冲击竖卡",
        "motion_profile": "kinetic_slam_tight",
        "css": css_pack(["sparkle-dots"]),
        "stagger_frames": 12,
        "mid_effect": "particle_dust",
    },
    {
        "id": "L08_glass_purple",
        "name": "紫雾玻璃竖卡",
        "motion_profile": "glass_card_stack",
        "css": css_pack(["soft-purple-gradient", "github-badge"]),
        "stagger_frames": 15,
        "mid_effect": "typewriter",
    },
    {
        "id": "L09_shake_warm",
        "name": "暖色强调竖卡",
        "motion_profile": "shake_emphasis",
        "css": css_pack(["soft-purple-gradient", "sparkle-dots"]),
        "stagger_frames": 14,
        "mid_effect": "glow_ring",
    },
    {
        "id": "L10_glass_cta_ready",
        "name": "收束型玻璃竖卡",
        "motion_profile": "glass_card_stack",
        "css": css_pack(["sparkle-dots", "pulse-button"]),
        "stagger_frames": 14,
        "mid_effect": "typewriter",
    },
)

TITLE_LAYOUT = {
    "id": "L00_title_hook",
    "name": "片头爆款钩子",
    "motion_profile": "flash_hook_smash",
    "css": css_pack(
        ["text-stroke-yellow", "rank-number", "sparkle-dots", "github-badge", "corner-brackets"]
    ),
}

CTA_LAYOUT = {
    "id": "L99_cta_follow",
    "name": "片尾关注引导",
    "motion_profile": "cta_pulse_arrow",
    "css": ["soft-purple-gradient", "pulse-button", "sparkle-dots", "github-badge"],
}


def layout_for_content_index(ci: int) -> dict[str, Any]:
    return dict(DOUYIN_CONTENT_LAYOUTS[ci % len(DOUYIN_CONTENT_LAYOUTS)])


def layout_assignment_table(slides: list[dict]) -> list[dict[str, str]]:
    """导出每镜排型分配（供报告）。"""
    rows: list[dict[str, str]] = []
    ci = 0
    for i, s in enumerate(slides):
        st = str(s.get("type") or "")
        if st == "title_card":
            rows.append({"slide": str(i), "type": st, "layout_id": TITLE_LAYOUT["id"], "name": TITLE_LAYOUT["name"]})
        elif st == "cta_card":
            rows.append({"slide": str(i), "type": st, "layout_id": CTA_LAYOUT["id"], "name": CTA_LAYOUT["name"]})
        elif st == "content_card" or s.get("scene_focus"):
            pack = layout_for_content_index(ci)
            ci += 1
            rows.append(
                {
                    "slide": str(i),
                    "type": st or "content_card",
                    "layout_id": pack["id"],
                    "name": pack["name"],
                    "motion_profile": pack["motion_profile"],
                }
            )
    return rows
