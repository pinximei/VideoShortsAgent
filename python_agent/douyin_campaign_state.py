"""十轮大循环间递进调参（每轮真实改分镜参数）。"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class CampaignState:
    cycle: int = 0
    stagger_frames: int = 14
    max_chars_per_page: int = 20
    caption_bottom_px: int = 340
    opening_duration_frames: int = 165
    caption_letter_spacing: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> CampaignState:
        if not d:
            return cls()
        kw = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        return cls(**kw)


def apply_state_to_slides(slides: list[dict[str, Any]], state: CampaignState) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in slides:
        slide = dict(s)
        mp = dict(slide.get("motion_params") or {})
        mp["staggerFrames"] = state.stagger_frames
        mp["maxCharsPerPage"] = state.max_chars_per_page
        mp["captionBottomPx"] = state.caption_bottom_px
        mp["captionLetterSpacing"] = state.caption_letter_spacing
        slide["motion_params"] = mp
        if str(slide.get("type")) == "title_card":
            slide["opening_duration_frames"] = state.opening_duration_frames
        out.append(slide)
    return out


def tune_state_from_issues(state: CampaignState, issues: list[str]) -> CampaignState:
    s = CampaignState(**state.to_dict())
    for iss in issues:
        if "stagger_too_slow" in iss and s.stagger_frames > 10:
            s.stagger_frames -= 1
        if "caption_letter_spacing_wide" in iss and s.caption_letter_spacing > 0:
            s.caption_letter_spacing = 0
        if "caption_chars_too_few" in iss and s.max_chars_per_page < 20:
            s.max_chars_per_page = min(20, s.max_chars_per_page + 1)
        if "caption_bottom_too_low" in iss and s.caption_bottom_px < 380:
            s.caption_bottom_px += 12
        if "opening_too_fast" in iss and s.opening_duration_frames < 195:
            s.opening_duration_frames += 10
    return s
