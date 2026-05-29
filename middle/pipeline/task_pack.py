"""读取中间层任务目录（brief、LLM 产物、publish 文案）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_brief(task_dir: Path) -> dict[str, Any]:
    path = task_dir / "brief.json"
    if not path.is_file():
        raise FileNotFoundError(f"缺少 brief.json: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_video_plan(task_dir: Path, platform_id: str) -> dict[str, Any]:
    """读取 llm/video_clips_{platform}.json（clips + effects）。"""
    path = task_dir / "llm" / f"video_clips_{platform_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"缺少大模型分镜: {path}（请先运行中间层 llm 生成）")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    clips = data.get("clips") or []
    if not clips:
        raise ValueError(f"分镜为空: {path}")
    return data


def load_video_clips(task_dir: Path, platform_id: str) -> list[dict[str, Any]]:
    return load_video_plan(task_dir, platform_id)["clips"]


def load_script(task_dir: Path, platform_id: str) -> str:
    if platform_id == "xhs":
        p = task_dir / "script_xhs.txt"
        if p.is_file():
            return p.read_text(encoding="utf-8").strip()
    p = task_dir / "script.txt"
    return p.read_text(encoding="utf-8").strip() if p.is_file() else ""


def article_manifest_entries(task_dir: Path) -> list[dict[str, Any]]:
    from .platform_presets import DEFAULT_ARTICLE_PLATFORMS, get_platform_preset

    entries: list[dict[str, Any]] = []
    for pid in DEFAULT_ARTICLE_PLATFORMS:
        preset = get_platform_preset(pid)
        rel = f"publish/{preset.publish_file}"
        abs_path = task_dir / rel
        preview = abs_path.read_text(encoding="utf-8")[:120] if abs_path.is_file() else ""
        entries.append(
            {
                "platform": pid,
                "label": preset.label,
                "content_kind": "article",
                "path": str(abs_path) if abs_path.is_file() else None,
                "text_preview": preview,
            }
        )
    return entries
