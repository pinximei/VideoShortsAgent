"""抖音模板成片镜像到其它视频渠道（如小红书），避免重复渲染。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .config import PipelineConfig
from .platform_presets import video_platforms


def render_platform_ids(cfg: PipelineConfig, platforms: list[str] | None = None) -> list[str]:
    """实际需要跑渲染引擎的平台列表。"""
    template = (cfg.render_video_template_platform or "").strip()
    if template:
        return [template]
    return [p.id for p in video_platforms(platforms or cfg.render_platforms)]


def publish_video_platform_ids(cfg: PipelineConfig) -> list[str]:
    """发布/门禁要求的视频平台（含镜像目标）。"""
    return [p.id for p in video_platforms(cfg.render_platforms)]


def apply_video_mirror(cfg: PipelineConfig, task_dir: Path) -> list[str]:
    """
    将 template 平台 mp4 复制到 mirror_video_to 列表。
    返回本次写入的目标平台 id。
    """
    task_dir = task_dir.resolve()
    src_id = (cfg.render_video_template_platform or "douyin").strip() or "douyin"
    targets = [t.strip() for t in (cfg.render_mirror_video_to or []) if t.strip()]
    targets = [t for t in targets if t != src_id]
    if not targets:
        return []

    src = task_dir / "videos" / f"{src_id}.mp4"
    if not src.is_file():
        raise FileNotFoundError(f"镜像源成片不存在: {src}")

    written: list[str] = []
    videos_dir = task_dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    llm_dir = task_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)
    src_plan = llm_dir / f"video_clips_{src_id}.json"
    plan_data: dict[str, Any] = {}
    if src_plan.is_file():
        try:
            plan_data = json.loads(src_plan.read_text(encoding="utf-8"))
        except Exception:
            plan_data = {}

    for tgt in targets:
        dst = videos_dir / f"{tgt}.mp4"
        shutil.copy2(src, dst)
        written.append(tgt)
        if plan_data:
            mirrored = dict(plan_data)
            mirrored["mirrored_from"] = src_id
            (llm_dir / f"video_clips_{tgt}.json").write_text(
                json.dumps(mirrored, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    meta_path = task_dir / "video_mirror.json"
    meta_path.write_text(
        json.dumps(
            {"source": src_id, "targets": targets, "source_path": str(src)},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return written
