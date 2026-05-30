"""加载 aisoul-pipeline 任务目录中的 brief / script / publish 文案。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .platform_presets import (
    DEFAULT_ARTICLE_PLATFORMS,
    DEFAULT_VIDEO_PLATFORMS,
    PlatformPreset,
    get_platform_preset,
    is_video_platform,
)


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def parse_script_txt(text: str) -> dict[str, Any]:
    """解析 Pipeline 生成的 script.txt。"""
    hook = ""
    cta = ""
    points: list[str] = []

    hook_m = re.search(r"【钩子】\s*(.+)", text)
    if hook_m:
        hook = hook_m.group(1).strip()

    cta_m = re.search(r"【引导】\s*(.+)", text, re.DOTALL)
    if cta_m:
        cta = cta_m.group(1).strip()

    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^\d+\.\s*(.+)$", line)
        if m:
            points.append(m.group(1).strip())

    return {"hook": hook, "talking_points": points, "cta": cta}


def load_publish_meta(task_dir: Path) -> dict[str, dict[str, str]]:
    publish = task_dir / "publish"
    if not publish.is_dir():
        return {}
    meta: dict[str, dict[str, str]] = {}
    mapping = {
        "douyin": ["douyin_title.txt", "douyin_tags.txt"],
        "xhs": ["xhs_title.txt", "xhs_body.txt"],
        "toutiao": ["toutiao_micro.txt"],
        "douban": ["douban_note.txt"],
    }
    for platform, files in mapping.items():
        entry: dict[str, str] = {}
        for fname in files:
            p = publish / fname
            if p.is_file():
                key = fname.replace(".txt", "")
                entry[key] = _read_text(p)
        if entry:
            meta[platform] = entry
    return meta


def load_pipeline_pack(task_dir: str | Path) -> dict[str, Any]:
    """
    读取 Pipeline 任务目录。

    期望结构::
        {task_dir}/brief.json
        {task_dir}/script.txt
        {task_dir}/publish/...
    """
    root = Path(task_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"任务目录不存在: {root}")

    brief_path = root / "brief.json"
    if not brief_path.is_file():
        raise FileNotFoundError(f"缺少 brief.json: {brief_path}")

    brief = json.loads(brief_path.read_text(encoding="utf-8-sig"))
    script_path = root / "script.txt"
    script_text = _read_text(script_path)
    script_xhs = _read_text(root / "script_xhs.txt")
    script_parts = parse_script_txt(script_text) if script_text else {}

    # script.txt 可覆盖 brief 中口播字段（以 Pipeline 落盘为准）
    if script_parts.get("hook"):
        brief["hook"] = script_parts["hook"]
    if script_parts.get("talking_points"):
        brief["talking_points"] = script_parts["talking_points"]
    if script_parts.get("cta"):
        brief["cta"] = script_parts["cta"]

    return {
        "task_dir": str(root),
        "brief": brief,
        "script_text": script_text,
        "script_xhs": script_xhs,
        "publish": load_publish_meta(root),
    }


def save_video_clips_plan(
    task_dir: str | Path,
    platform_id: str,
    clips: list[dict[str, Any]],
    *,
    effects: dict[str, Any] | None = None,
    source: str = "render",
    render_status: str = "ok",
    extra: dict[str, Any] | None = None,
) -> Path:
    """渲染后写回 llm/video_clips_{platform}.json（含 B-roll 时间轴）。"""
    root = Path(task_dir).resolve()
    llm_dir = root / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)
    path = llm_dir / f"video_clips_{platform_id}.json"
    payload: dict[str, Any] = {
        "clips": clips,
        "platform": platform_id,
        "effects": effects or {},
        "source": source,
        "render_status": render_status,
    }
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def brief_to_clips(brief: dict[str, Any], preset: PlatformPreset) -> list[dict[str, Any]]:
    """将 brief 口播结构转为 RenderSkill / DubbingSkill 所需的 clips（不经 LLM）。"""
    from python_agent.pipeline_quality import brief_for_platform

    brief = brief_for_platform(brief, preset)
    clips: list[dict[str, Any]] = []

    hook = (brief.get("hook") or "").strip()
    if hook:
        clips.append(
            {
                "tts_text": hook,
                "hook_text": hook[:20],
                "caption_style": preset.hook_caption_style,
                "transition_to_next": preset.hook_transition,
                "start": 0.0,
                "end": 5.0,
            }
        )

    from python_agent.capabilities.clip_text import bullets_from_prose

    for point in brief.get("talking_points") or []:
        text = str(point).strip()
        if not text:
            continue
        entry: dict[str, Any] = {
            "tts_text": text,
            "hook_text": text[:24],
            "caption_style": preset.body_caption_style,
            "transition_to_next": preset.body_transition,
            "start": 0.0,
            "end": 8.0,
        }
        derived = bullets_from_prose(text)
        if len(derived) >= 2:
            entry["bullets"] = derived
        clips.append(entry)

    cta = (brief.get("cta") or "").strip()
    if cta:
        clips.append(
            {
                "tts_text": cta,
                "hook_text": "详情见简介",
                "caption_style": preset.cta_caption_style,
                "transition_to_next": "fade",
                "start": 0.0,
                "end": 5.0,
            }
        )

    if not clips:
        title = (brief.get("title") or "本期内容").strip()
        clips.append(
            {
                "tts_text": title,
                "hook_text": title[:24],
                "caption_style": preset.body_caption_style,
                "transition_to_next": preset.body_transition,
                "start": 0.0,
                "end": 8.0,
            }
        )

    return clips


def resolve_video_platforms(platforms: list[str] | None = None) -> list[PlatformPreset]:
    """仅返回需要出 mp4 的视频渠道（默认抖音 + 小红书）。"""
    ids = platforms or list(DEFAULT_VIDEO_PLATFORMS)
    out: list[PlatformPreset] = []
    for pid in ids:
        preset = get_platform_preset(pid)
        if preset.content_kind != "video":
            continue
        out.append(preset)
    if not out and platforms:
        raise ValueError(f"未包含视频渠道，视频仅支持: {', '.join(DEFAULT_VIDEO_PLATFORMS)}")
    return out or [get_platform_preset(p) for p in DEFAULT_VIDEO_PLATFORMS]


def resolve_platforms(platforms: list[str] | None = None) -> list[PlatformPreset]:
    """兼容旧名：等同于 resolve_video_platforms。"""
    return resolve_video_platforms(platforms)


def load_video_clips(task_dir: Path, platform_id: str) -> dict[str, Any] | None:
    """读取中间层 LLM 落盘的分镜方案 llm/video_clips_{platform}.json。"""
    path = task_dir / "llm" / f"video_clips_{platform_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("clips"):
        return data
    return None


def article_platform_manifest(task_dir: Path, publish: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    """文章渠道：指向 publish 目录已有文案，不生成视频。"""
    entries: list[dict[str, Any]] = []
    for pid in DEFAULT_ARTICLE_PLATFORMS:
        preset = get_platform_preset(pid)
        meta = publish.get(pid) or {}
        text_key = preset.publish_file.replace(".txt", "") if preset.publish_file else ""
        text = meta.get(text_key, "")
        rel_path = f"publish/{preset.publish_file}" if preset.publish_file else ""
        abs_path = str(task_dir / rel_path) if rel_path else ""
        entries.append(
            {
                "platform": preset.id,
                "label": preset.label,
                "content_kind": "article",
                "path": abs_path if rel_path and (task_dir / rel_path).is_file() else None,
                "text_preview": (text or "")[:120],
            }
        )
    return entries
