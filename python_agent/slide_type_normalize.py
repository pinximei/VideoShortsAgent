"""Compose 产出常带 title_card:true 而非 type；统一为 title/content/cta。"""
from __future__ import annotations

from typing import Any


def normalize_slide_types(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not slides:
        return []
    out: list[dict[str, Any]] = []
    n = len(slides)
    for i, slide in enumerate(slides):
        s = dict(slide)
        st = str(s.get("type") or s.get("unit") or "").strip().lower()
        is_cta = st == "cta_card" or bool(str(s.get("cta_text") or s.get("cta") or "").strip())
        if i == n - 1 and (is_cta or "cta" in str(s.get("scene_number") or "").lower()):
            s["type"] = "cta_card"
            s["scene_focus"] = False
        elif i == 0 or (st == "title_card" and not s.get("scene_focus")):
            s["type"] = "title_card"
            s["scene_focus"] = False
        else:
            s["type"] = "content_card"
            s["scene_focus"] = True
        s.pop("title_card", None)
        s.pop("title_card_type", None)
        out.append(s)
    if str(out[-1].get("type")) != "cta_card" and n >= 2:
        last = out[-1]
        if str(last.get("tts_text") or "").find("关注") >= 0 or str(last.get("heading") or "").find("关注") >= 0:
            last["type"] = "cta_card"
            last["scene_focus"] = False
    return out
