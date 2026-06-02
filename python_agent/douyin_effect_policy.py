"""抖音中部动效策略：强动效限量、liquid 仅 hero。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_POLICY_PATH = Path(__file__).resolve().parents[1] / "templates" / "douyin_effect_policy.json"
_CACHE: dict[str, Any] | None = None


def load_effect_policy() -> dict[str, Any]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _POLICY_PATH.is_file():
        _CACHE = json.loads(_POLICY_PATH.read_text(encoding="utf-8"))
    else:
        _CACHE = {
            "default_mid_effect": "glow_ring",
            "max_liquid_slides": 1,
            "liquid_triggers": ["自然语言"],
        }
    return _CACHE


def _tts_triggers_liquid(tts: str, triggers: list[str]) -> bool:
    t = tts or ""
    return any(k in t for k in triggers)


def apply_douyin_effect_policy(
    slides: list[dict[str, Any]],
    *,
    platform: str = "douyin",
) -> list[dict[str, Any]]:
    if platform != "douyin":
        return slides
    policy = load_effect_policy()
    triggers = list(policy.get("liquid_triggers") or [])
    default_fx = str(policy.get("default_mid_effect") or "glow_ring")
    stat_fx = str(policy.get("stat_slide_effect") or "glow_scan")
    cta_fx = str(policy.get("cta_mid_effect") or "glow_ring")
    max_liquid = int(policy.get("max_liquid_slides") or 1)
    strong_used = 0
    liquid_used = 0
    out: list[dict[str, Any]] = []

    for s in slides:
        slide = dict(s)
        st = str(slide.get("type") or "")
        if st == "cta_card":
            slide["mid_effect"] = cta_fx
            slide["liquid_shake_hero_only"] = True
            out.append(slide)
            continue
        if not (slide.get("scene_focus") or st == "content_card"):
            out.append(slide)
            continue

        vt = str(slide.get("viz_type") or "none").lower()
        tts = str(slide.get("tts_text") or "")
        want_liquid = (
            liquid_used < max_liquid
            and _tts_triggers_liquid(tts, triggers)
            and strong_used < int(policy.get("max_strong_per_video") or 2)
        )
        if want_liquid:
            slide["mid_effect"] = "liquid_shake"
            slide["liquid_shake_hero_only"] = True
            liquid_used += 1
            strong_used += 1
        elif vt == "stat":
            slide["mid_effect"] = stat_fx
            slide["liquid_shake_hero_only"] = True
        else:
            fx = str(slide.get("mid_effect") or default_fx)
            if fx in ("liquid_shake", "shake_emphasis"):
                fx = default_fx
            slide["mid_effect"] = fx
            slide["liquid_shake_hero_only"] = fx == "liquid_shake"
        out.append(slide)
    return out
