#!/usr/bin/env python3
"""
生成动效风格目录（100 套）— 按「动效档案 + 节奏参数」而非配色变体。

参考：docs/MOTION_STYLE_RESEARCH.md
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "templates" / "motion_templates" / "catalog.json"

# 动效档案：每套是独立编排逻辑（见 remotion_effects/src/motion/）
PROFILES = [
    ("github_daily_hook", "GitHub日更·钩子砸字", "每天分享一个GitHub类开场：角标+按词弹射", "github"),
    ("github_daily_bullets", "GitHub日更·要点滑轨", "正文要点从右侧滑入+竖线", "github"),
    ("tiktok_word_pop", "抖音口播·当前词高亮", "Remotion TikTok caption 风格逐词放大", "tiktok"),
    ("tiktok_phrase_pages", "抖音口播·短语分页", "多词组合分页切换感", "tiktok"),
    ("kinetic_slam_tight", "快闪·紧砸字", "测评快闪极短间隔字词 spring", "kinetic"),
    ("kinetic_slam_loose", "快闪·松砸字", "字词弹射节奏略慢", "kinetic"),
    ("flash_hook_smash", "快闪·首帧砸屏", "首屏字符级放大砸入", "kinetic"),
    ("typewriter_terminal", "终端·打字机", "等宽光标打字", "terminal"),
    ("episode_counter", "日更·序号冲击", "大序号后出标题", "github"),
    ("glitch_hook_clean", "钩子Glitch·正文稳", "仅开场 glitch", "kinetic"),
    ("bullet_rail_right", "要点·右轨", "条目标签右滑入", "github"),
    ("bullet_stagger_up", "要点·上浮", "条目自下而上", "kinetic"),
    ("minimal_headline", "极简·单行标题", "单行呼吸 scale", "minimal"),
    ("cta_pulse_arrow", "CTA·脉冲箭头", "结尾按钮脉冲", "github"),
    ("mono_code_rain", "背景·代码雨", "锐代码雨+网格", "terminal"),
    ("split_mask_reveal", "遮罩·横向揭示", "标题横向 mask 揭示", "kinetic"),
    ("glass_card_stack", "玻璃·卡片堆叠", "要点玻璃卡片 stagger", "tiktok"),
    ("marquee_ticker", "跑马·顶栏", "顶部 ticker 滚动", "tiktok"),
    ("shake_emphasis", "强调·微震", "关键词微震强调", "kinetic"),
    ("product_split_frame", "产品·分栏", "左文右图分栏（无图则纯文）", "minimal"),
]

# 5 组节奏参数 — 来自预研（见 docs/MOTION_PRESEARCH_REPORT.md），非拍脑袋配色
# - 200ms: Remotion template-tiktok 注释「逐词」
# - 800ms: B站剪映教程样本帧差实测 (BV196xNzDEU9)
# - 1200ms: Remotion 官方 SWITCH_CAPTIONS_EVERY_MS
# - 2500ms: 竖屏知识类 2–4 秒/信息点（工作流文档中值）
PARAM_SETS = [
    {
        "staggerFrames": 2,
        "springDamping": 12,
        "springStiffness": 200,
        "wordsPerPageMs": 200,
        "research_status": "validated",
        "research_ref": "remotion-dev/template-tiktok index.tsx comment",
    },
    {
        "staggerFrames": 4,
        "springDamping": 14,
        "springStiffness": 160,
        "wordsPerPageMs": 800,
        "research_status": "validated",
        "research_ref": "research/motion/reports subtitle_motion BV196xNzDEU9",
    },
    {
        "staggerFrames": 5,
        "springDamping": 14,
        "springStiffness": 140,
        "wordsPerPageMs": 1200,
        "research_status": "validated",
        "research_ref": "remotion-dev/template-tiktok SWITCH_CAPTIONS_EVERY_MS=1200",
    },
    {
        "staggerFrames": 6,
        "springDamping": 16,
        "springStiffness": 110,
        "wordsPerPageMs": 2500,
        "research_status": "validated",
        "research_ref": "aistacknav 竖屏知识类 2-4s/info",
    },
    {
        "staggerFrames": 7,
        "springDamping": 18,
        "springStiffness": 95,
        "wordsPerPageMs": 1400,
        "research_status": "hypothesis",
        "research_ref": "待抖音成片样本标定",
    },
]

SLIDE_ROLE_PROFILE = {
    "title_card": ["github_daily_hook", "episode_counter", "kinetic_slam_tight", "flash_hook_smash", "glitch_hook_clean", "tiktok_word_pop"],
    "content_card": ["github_daily_bullets", "bullet_rail_right", "bullet_stagger_up", "glass_card_stack", "minimal_headline"],
    "cta_card": ["cta_pulse_arrow", "kinetic_slam_loose", "shake_emphasis"],
}


def generate() -> list[dict]:
    templates: list[dict] = []
    idx = 0
    for profile_id, name, reference, theme_key in PROFILES:
        for pi, params in enumerate(PARAM_SETS):
            idx += 1
            tid = f"{profile_id}_p{pi + 1:02d}"
            motion_params = {k: v for k, v in params.items() if k not in ("research_status", "research_ref")}
            templates.append(
                {
                    "id": tid,
                    "name": f"{name} ·节奏{pi + 1}",
                    "motion_profile": profile_id,
                    "motion_params": motion_params,
                    "research_status": params.get("research_status", "hypothesis"),
                    "research_ref": params.get("research_ref", ""),
                    "reference": reference,
                    "theme": theme_key,
                    "for_slide_types": [
                        st
                        for st, profs in SLIDE_ROLE_PROFILE.items()
                        if profile_id in profs
                    ]
                    or ["content_card"],
                    "caption_style": "spring" if "tiktok" in profile_id else "typewriter" if "terminal" in profile_id else "fade",
                    "transition": ["circleopen", "wipeleft", "slideup", "fade", "dissolve"][pi % 5],
                }
            )
    return templates


def main() -> int:
    templates = generate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    catalog = {
        "version": 2,
        "count": len(templates),
        "description": "动效档案目录：每条模板绑定 motion_profile + motion_params，非配色变体。",
        "profiles": [p[0] for p in PROFILES],
        "templates": templates,
    }
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(templates)} motion-style templates -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
