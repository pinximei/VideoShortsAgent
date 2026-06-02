"""抖音 LLM 分镜测试夹具。"""
from __future__ import annotations

from typing import Any

from python_agent.douyin_layout_registry import css_pack, layout_for_content_index
from python_agent.douyin_shot_designer import ShotDesign


def mock_llm_shot_plans(slides: list[dict], brief: dict) -> dict[int, ShotDesign]:
    """模拟 LLM 返回的逐镜细设计（仅测试用）。"""
    del brief
    plans: dict[int, ShotDesign] = {}
    layouts = ("framed", "steps", "compare")
    ci = 0
    for i, s in enumerate(slides):
        st = str(s.get("type") or "")
        if st == "title_card":
            plans[i] = ShotDesign(
                hero_title=str(s.get("heading") or "OpenHands")[:14],
                subtitle_cards=[],
                mid_info_layout="keywords",
                mid_effect="typewriter",
                motion_profile="flash_hook_smash",
                css_decorations=css_pack(["github-badge", "corner-brackets"]),
                design_rationale="片头 LLM mock：仓库名+GitHub 系列钩子",
            )
        elif st == "content_card" or s.get("scene_focus"):
            layout = layouts[ci % 3]
            pack = layout_for_content_index(ci)
            plans[i] = ShotDesign(
                hero_title="核心亮点",
                subtitle_cards=["副标题A", "副标题B"],
                mid_info_layout=layout,
                mid_effect="glow_ring",
                motion_profile=str(pack.get("motion_profile") or "glass_card_stack"),
                css_decorations=css_pack(
                    ["odometer-stars"] if ci == 0 else ["float-icon"]
                ),
                viz_type="stat" if ci == 0 else "none",
                stat_value="1.2万 Star" if ci == 0 else "",
                design_rationale=f"mock 内容镜{ci} 语义设计 → {layout}",
            )
            ci += 1
    return plans
