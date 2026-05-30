from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .config import PipelineConfig, repo_root
from .platform_presets import get_platform_preset, video_platforms
from .task_pack import article_manifest_entries, load_brief, load_video_plan


def _ensure_repo_path() -> None:
    root = str(repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def render_from_llm_plan(
    cfg: PipelineConfig,
    task_dir: Path,
    platform_id: str,
    *,
    broll_path: str | None = None,
) -> Path:
    _ensure_repo_path()
    from python_agent.vsa_render import render_from_plan

    preset = get_platform_preset(platform_id)
    broll = (broll_path or cfg.broll_template or "").strip()
    plan = load_video_plan(task_dir, platform_id)
    out = task_dir / "videos" / f"{platform_id}.mp4"
    render_from_plan(
        clips=plan["clips"],
        broll_path=broll,
        output_path=str(out),
        platform=platform_id,
        voice=preset.voice,
        max_seconds=preset.max_seconds,
        width=preset.width,
        height=preset.height,
        skip_tts=cfg.render_skip_tts,
        work_dir=str(task_dir / "videos" / f"_work_{platform_id}"),
        effects=plan.get("effects"),
        use_remotion=cfg.render_use_remotion,
        task_dir=str(task_dir),
    )
    return out


def render_task_videos(
    cfg: PipelineConfig,
    task_dir: Path,
    *,
    platforms: list[str] | None = None,
) -> dict[str, Any] | None:
    if not cfg.render_enabled:
        return None

    task_dir = task_dir.resolve()
    brief = load_brief(task_dir)
    videos: list[dict[str, Any]] = []

    for preset in video_platforms(platforms or cfg.render_platforms):
        path = render_from_llm_plan(cfg, task_dir, preset.id)
        videos.append({"platform": preset.id, "label": preset.label, "path": str(path), "content_kind": "video"})

    import json

    articles = article_manifest_entries(task_dir)
    manifest = {
        "content_key": brief.get("content_key"),
        "article_id": brief.get("article_id"),
        "title": brief.get("title"),
        "videos": videos,
        "articles": articles,
        "executor": "python_agent.vsa_render.render_from_plan",
    }
    manifest_path = task_dir / "videos" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        from .render_verify import run_post_render_verify

        run_post_render_verify(task_dir, platforms=cfg.render_platforms)
    except Exception:
        pass

    primary = task_dir / "videos" / "douyin.mp4"
    legacy = task_dir / "video.mp4"
    if primary.is_file():
        legacy.write_bytes(primary.read_bytes())

    return {
        "status": "ok",
        "task_dir": str(task_dir),
        "manifest": str(manifest_path),
        "videos": videos,
        "articles": articles,
        "primary_video": str(legacy) if legacy.is_file() else None,
    }
