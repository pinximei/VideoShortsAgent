"""兼容旧 import；请改用 pipeline.vsa。"""
from __future__ import annotations

from pathlib import Path

from .config import PipelineConfig
from .models import VideoBrief
from .vsa import render_task_videos


def render_pipeline_videos(
    cfg: PipelineConfig,
    brief: VideoBrief,
    output_dir: Path,
    *,
    platforms: list[str] | None = None,
) -> dict | None:
    if platforms:
        return render_task_videos(cfg, output_dir, platforms=platforms)
    return render_task_videos(cfg, output_dir)


def render_douyin_pack(
    cfg: PipelineConfig,
    brief: VideoBrief,
    output_dir: Path,
    *,
    segments: str | None = None,
) -> Path | None:
    mode = (cfg.render_mode or "pipeline").strip().lower()
    if mode in ("pipeline", "pipeline_multi", "multi"):
        result = render_task_videos(cfg, output_dir)
        if not result:
            return None
        primary = result.get("primary_video")
        return Path(primary) if primary and Path(primary).is_file() else None
    result = render_task_videos(cfg, output_dir)
    if not result:
        return None
    primary = result.get("primary_video")
    return Path(primary) if primary and Path(primary).is_file() else None
