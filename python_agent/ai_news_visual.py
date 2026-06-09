"""爱资讯款式：强对比渐变 / 粒子 / Web3 背景（与 GitHub 暗色区分开）。"""
from __future__ import annotations

from typing import Any


def apply_variant_visual_dna(
    slides: list[dict[str, Any]],
    template: dict[str, Any],
) -> list[dict[str, Any]]:
    """把 catalog 里的 gradient_colors / color_mood 写入每镜 visual_design。"""
    grad = list(template.get("gradient_colors") or template.get("title", {}).get("background_colors") or [])
    mood = str(template.get("color_mood") or "warm-sunrise")
    variant = str(template.get("background_variant") or "mesh-aurora")
    particle = str(template.get("particle_type") or "bokeh")
    accent = str(template.get("accent_color") or "#FF9F43")
    accent2 = str(template.get("accent_color2") or "#FFD93D")
    text_color = str(template.get("text_color") or "#fff8f0")
    use_web3 = bool(template.get("use_web3_background", True))

    out: list[dict[str, Any]] = []
    for s in slides:
        slide = dict(s)
        vd = dict(slide.get("visual_design") or {})
        if grad:
            vd["colors"] = grad
        vd["color_mood"] = mood
        vd["background_variant"] = variant
        vd["particle_type"] = particle
        vd["accent_color"] = accent
        vd["accent_color2"] = accent2
        vd["text_color"] = text_color
        vd["use_web3_background"] = use_web3
        slide["visual_design"] = vd
        if grad and str(slide.get("type")) in ("title_card", "content_card") or slide.get("scene_focus"):
            slide["background_color"] = grad[0]
        out.append(slide)
    return out
