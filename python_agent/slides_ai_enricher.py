"""分镜视觉补全：默认无图表；仅保留 LLM 已判定的 viz。"""
from __future__ import annotations

import re
from typing import Any

from python_agent.slides_llm_director import _apply_viz, _strip_bottom_chart


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _heuristic_summary_lines(tts: str, feature: str, heading: str, *, max_lines: int = 3) -> list[str]:
    t = _plain(tts) or _plain(feature) or _plain(heading)
    if not t:
        return ["核心亮点"]
    parts = re.split(r"(?<=[。！？；，,])", t)
    parts = [p.strip("，,。！？ ") for p in parts if 4 <= len(p.strip()) <= 16]
    lines: list[str] = []
    if feature and len(feature) <= 14:
        lines.append(feature)
    for p in parts:
        if len(lines) >= max_lines:
            break
        lines.append(p[:14])
    while len(lines) < 2:
        lines.append("一步上手" if len(lines) == 0 else "值得试试")
    return lines[:max_lines]


def enrich_slides_visual_payload(
    slides: list[dict[str, Any]],
    brief: dict[str, Any],
    platform: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for slide in slides:
        s = dict(slide)
        st = str(s.get("type") or "")
        s["css_decorations"] = _strip_bottom_chart(list(s.get("css_decorations") or []))

        if st in ("content_card",) or s.get("scene_focus"):
            tts = str(s.get("tts_text") or "")
            if not s.get("summary_lines"):
                s["summary_lines"] = _heuristic_summary_lines(
                    tts,
                    str(s.get("feature_label") or ""),
                    str(s.get("heading") or ""),
                )
            if not s.get("viz_type"):
                _apply_viz(s, "none", [], "", "", "", tts=tts)
            s.setdefault("show_kinetic_wall", s.get("viz_type") == "none")
            if s.get("viz_type") != "none":
                s["show_kinetic_wall"] = False
        else:
            s["viz_type"] = "none"
            s["show_chart"] = False
            s["show_kinetic_wall"] = False

        out.append(s)
    return out
