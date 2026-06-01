"""分平台多场景拆镜：抖音深暖色 / 小红书冷色 editorial，多转场。"""
from __future__ import annotations

import copy
import re
from typing import Any

PLATFORM_CFG: dict[str, dict[str, Any]] = {
    "douyin": {
        "bgs": ("#120908", "#1a100c", "#221510", "#18100a", "#1f120c"),
        "profiles": (
            "tiktok_phrase_pages",
            "bullet_rail_right",
            "shake_emphasis",
            "kinetic_slam_tight",
            "glass_card_stack",
        ),
        "css": (
            ["daily-video-tag", "github-badge", "stat-pill-row"],
            ["rank-number", "stat-pill-row", "odometer-stars"],
            ["github-badge", "accent-orange-word", "float-icon"],
            ["text-stroke-yellow", "float-icon"],
            ["stat-pill-row", "odometer-stars"],
        ),
        "transitions": ("circleopen", "wipeleft", "slideup", "wipeleft", "slideright", "fade"),
    },
    "xhs": {
        "bgs": ("#0f1419", "#151c28", "#1a2332", "#121a24", "#182030"),
        "profiles": (
            "split_mask_reveal",
            "bullet_rail_right",
            "minimal_headline",
            "shake_emphasis",
            "glass_card_stack",
        ),
        "css": (
            ["repo-header", "pill-badge"],
            ["stat-pill-row", "rank-number"],
            ["accent-orange-word", "pill-badge"],
            ["rank-number", "float-icon"],
            ["stat-pill-row", "odometer-stars"],
        ),
        "transitions": ("dissolve", "slideup", "wipeleft", "circleopen", "slideright", "fade"),
    },
}


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _split_tts_for_parts(text: str, n: int) -> list[str]:
    t = _plain(text)
    if n <= 1 or not t:
        return [t] if t else [""]
    clauses = re.split(r"(?<=[。！？；，,])", t)
    clauses = [c.strip() for c in clauses if c.strip()]
    if not clauses:
        clauses = [t]
    buckets: list[list[str]] = [[] for _ in range(n)]
    weights = [0] * n
    for c in clauses:
        idx = weights.index(min(weights))
        buckets[idx].append(c)
        weights[idx] += len(c)
    return [_plain("".join(b)) or t for b in buckets]


def _expand_content_scenes(
    slide: dict[str, Any],
    *,
    cfg: dict[str, Any],
    scene_i: int,
    n: int,
    bullet_dicts: list[dict],
) -> tuple[list[dict[str, Any]], int]:
    out: list[dict[str, Any]] = []
    tts_parts = _split_tts_for_parts(str(slide.get("tts_text") or ""), n)
    bgs = cfg["bgs"]
    profiles = cfg["profiles"]
    css_list = cfg["css"]
    trans = cfg["transitions"]

    for j in range(n):
        b = bullet_dicts[j] if j < len(bullet_dicts) else bullet_dicts[-1]
        ns = copy.deepcopy(slide)
        ns["scene_index"] = scene_i
        ns["scene_focus"] = True
        ns["heading"] = str(slide.get("heading") or "") if j == 0 else ""
        ns["feature_label"] = _plain(str(b.get("text", "")))
        ns["bullets"] = [b]
        part = tts_parts[j] if j < len(tts_parts) else (tts_parts[-1] if tts_parts else "")
        if not _plain(part):
            part = ns["feature_label"] + "。"
        ns["tts_text"] = part
        si = scene_i % len(bgs)
        ns["background_color"] = bgs[si]
        ns["motion_profile"] = profiles[si % len(profiles)]
        ns["css_decorations"] = list(css_list[si % len(css_list)])
        ns["transition_to_next"] = trans[min(scene_i + 1, len(trans) - 1)]
        ns["mid_screen_kinetic"] = False
        effects = ("glow_ring", "typewriter", "particle_dust", "bracket_slam", "glow_scan")
        ns["mid_effect"] = effects[scene_i % len(effects)]
        scene_i += 1
        out.append(ns)
    return out, scene_i


def expand_platform_scenes(
    slides: list[dict[str, Any]],
    platform: str,
) -> list[dict[str, Any]]:
    plat = (platform or "").strip().lower()
    cfg = PLATFORM_CFG.get(plat)
    if not cfg or any(s.get("scene_focus") for s in slides):
        return slides

    out: list[dict[str, Any]] = []
    scene_i = 0
    slide_count = len(slides)
    trans = cfg["transitions"]

    for idx, slide in enumerate(slides):
        st = str(slide.get("type") or "content_card")
        if st != "content_card":
            ns = copy.deepcopy(slide)
            ns["transition_to_next"] = trans[min(scene_i, len(trans) - 1)]
            out.append(ns)
            if st == "title_card":
                scene_i += 1
            continue

        bullets = slide.get("bullets") or []
        bullet_dicts = [
            b if isinstance(b, dict) else {"text": str(b)}
            for b in (bullets if isinstance(bullets, list) else [])
        ]
        bullet_dicts = [b for b in bullet_dicts if _plain(str(b.get("text", "")))]
        n = max(3, min(5, len(bullet_dicts) or 3))

        if len(bullet_dicts) < 2:
            ns = copy.deepcopy(slide)
            ns["scene_index"] = scene_i
            ns["scene_focus"] = True
            si = scene_i % len(cfg["bgs"])
            ns["background_color"] = cfg["bgs"][si]
            ns["motion_profile"] = cfg["profiles"][si % len(cfg["profiles"])]
            ns["css_decorations"] = list(cfg["css"][si % len(cfg["css"])])
            ns["transition_to_next"] = trans[min(scene_i + 1, len(trans) - 1)]
            scene_i += 1
            out.append(ns)
            continue

        expanded, scene_i = _expand_content_scenes(
            slide, cfg=cfg, scene_i=scene_i, n=n, bullet_dicts=bullet_dicts
        )
        out.extend(expanded)

    return out if out else slides
