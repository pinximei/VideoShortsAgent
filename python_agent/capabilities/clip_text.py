"""分镜 clip 文本字段（bullets / hook）解析。"""
from __future__ import annotations

import re
from typing import Any


def clip_bullets(clip: dict[str, Any]) -> list[str]:
    raw = clip.get("bullets")
    if isinstance(raw, list):
        return [str(b).strip() for b in raw if str(b).strip()][:4]
    hook = str(clip.get("hook_text") or "").strip()
    if not hook:
        return []
    if re.search(r"[\u00b7\u30fb、\n]", hook):
        parts = re.split(r"[\u00b7\u30fb、\n]+", hook)
        return [p.strip() for p in parts if p.strip()][:4]
    return []


def bullets_from_prose(text: str, *, max_items: int = 3) -> list[str]:
    """从一段正文拆出屏上要点（规则 fallback）。"""
    plain = re.sub(r"\s+", " ", (text or "").strip())
    if not plain:
        return []
    if re.search(r"[\u00b7\u30fb、]", plain):
        parts = re.split(r"[\u00b7\u30fb、]+", plain)
        out = [p.strip() for p in parts if len(p.strip()) >= 2]
        return out[:max_items]
    for sep in ("。", "；", ". "):
        if sep in plain:
            parts = [p.strip() for p in plain.split(sep) if len(p.strip()) >= 6]
            if len(parts) >= 2:
                return parts[:max_items]
    return []


def enrich_apps_platform_copy(copy: dict[str, Any], *, feed_kind: str = "apps") -> dict[str, Any]:
    """apps 稿：正文段缺 bullets 时从 hook_text 自动补全。"""
    if (feed_kind or "").strip().lower() != "apps":
        return copy
    out = dict(copy)
    for pid in ("douyin", "xhs"):
        block = out.get(pid)
        if not isinstance(block, dict):
            continue
        clips = block.get("clips")
        if not isinstance(clips, list):
            continue
        new_clips: list[dict[str, Any]] = []
        n = len(clips)
        for i, clip in enumerate(clips):
            if not isinstance(clip, dict):
                new_clips.append(clip)
                continue
            c = dict(clip)
            if not clip_bullets(c) and 0 < i < n - 1:
                derived = bullets_from_prose(str(c.get("hook_text") or c.get("tts_text") or ""))
                if len(derived) >= 2:
                    c["bullets"] = derived
            new_clips.append(c)
        block = dict(block)
        block["clips"] = new_clips
        out[pid] = block
    return out
