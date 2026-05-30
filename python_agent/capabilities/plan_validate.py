"""LLM 分镜 JSON 校验（入库/渲染前）。"""
from __future__ import annotations

from typing import Any

from .registry import STYLE_PRESETS, VALID_CAPTION_STYLES, VALID_TRANSITIONS, resolve_transition


def _clip_tts_len(clip: dict) -> int:
    return len(str(clip.get("tts_text") or clip.get("hook_text") or ""))


def validate_platform_video_block(
    platform_id: str,
    block: dict[str, Any],
    *,
    broll_seconds: float | None = None,
    max_tts_chars: int = 240,
) -> tuple[bool, str]:
    """校验单平台 douyin/xhs 块（含 clips + effects）。"""
    if not isinstance(block, dict):
        return False, "block_not_object"
    clips = block.get("clips")
    if not isinstance(clips, list) or not (2 <= len(clips) <= 4):
        return False, f"clips_count={len(clips) if isinstance(clips, list) else 0} need 2-4"

    effects = block.get("effects")
    if not isinstance(effects, dict):
        return False, "effects_missing"
    preset = str(effects.get("preset") or "").strip()
    if preset not in STYLE_PRESETS:
        return False, f"preset_invalid={preset!r}"

    total_tts = 0
    prev_end = -1.0
    for i, c in enumerate(clips):
        if not isinstance(c, dict):
            return False, f"clip_{i}_not_object"
        try:
            start = float(c.get("start", 0))
            end = float(c.get("end", 0))
        except (TypeError, ValueError):
            return False, f"clip_{i}_bad_time"
        if end <= start:
            return False, f"clip_{i}_end_before_start"
        if start < prev_end - 0.01:
            return False, f"clip_{i}_overlap_start"
        prev_end = end
        if broll_seconds and end > float(broll_seconds) + 0.5:
            return False, f"clip_{i}_exceeds_broll={broll_seconds:.0f}s"
        if not str(c.get("hook_text") or "").strip() and not str(c.get("tts_text") or "").strip():
            return False, f"clip_{i}_no_text"
        cs = str(c.get("caption_style") or "").strip()
        if cs and cs not in VALID_CAPTION_STYLES and cs not in STYLE_PRESETS:
            return False, f"clip_{i}_bad_caption_style={cs!r}"
        tr = str(c.get("transition_to_next") or "").strip()
        if tr and tr not in VALID_TRANSITIONS:
            return False, f"clip_{i}_bad_transition={tr!r}"
        total_tts += _clip_tts_len(c)

    if total_tts > max_tts_chars:
        return False, f"tts_total={total_tts} max={max_tts_chars}"
    if total_tts < 40:
        return False, f"tts_total={total_tts} too_short"

    last_tr = resolve_transition(
        str(clips[-1].get("transition_to_next") or ""),
        default="fade",
    )
    if last_tr not in ("fade", "dissolve"):
        return False, f"last_transition_should_be_fade got={last_tr}"

    title = str(block.get("title") or "").strip()
    if platform_id == "douyin" and not title:
        return False, "douyin_title_empty"
    if platform_id == "xhs" and not str(block.get("body") or "").strip():
        return False, "xhs_body_empty"

    return True, "ok"


def validate_platform_copy(
    copy: dict[str, Any],
    *,
    platforms: tuple[str, ...] = ("douyin", "xhs"),
    broll_seconds: float | None = None,
) -> tuple[bool, str]:
    """校验整份 platform_copy。"""
    if not isinstance(copy, dict):
        return False, "root_not_object"
    errors: list[str] = []
    for pid in platforms:
        block = copy.get(pid)
        if not isinstance(block, dict):
            errors.append(f"{pid}_missing")
            continue
        ok, msg = validate_platform_video_block(pid, block, broll_seconds=broll_seconds)
        if not ok:
            errors.append(f"{pid}:{msg}")
    if errors:
        return False, "; ".join(errors)
    return True, "ok"


def repair_prompt_note(reason: str) -> str:
    return (
        f"\n\n## 修复要求（上次校验失败：{reason}）\n"
        "请重新输出完整 JSON。clips 必须 2~4 段；effects.preset 必填且为合法风格名；"
        "每段 start/end 在 B-roll 时长内且不重叠；口播总字数≤220；末段 transition_to_next 为 fade。"
    )
