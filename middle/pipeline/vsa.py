from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    brief = load_brief(task_dir)

    from .media_probe import probe_video_duration
    from python_agent.capabilities.plan_validate import validate_platform_video_block
    from python_agent.capabilities.registry import merge_render_effects

    broll_sec = probe_video_duration(broll) if broll else None
    clips = list(plan.get("clips") or [])
    if broll_sec and clips:
        from python_agent.pipeline_media import prefetch_task_cover
        from python_agent.pipeline_render import sync_broll_timings_to_clips
        from python_agent.pipeline_input import save_video_clips_plan

        prefetch_task_cover(task_dir, brief)
        if sync_broll_timings_to_clips(clips, float(broll_sec)):
            prev_source = str(plan.get("source") or "pipeline_llm")
            save_video_clips_plan(
                task_dir,
                platform_id,
                clips,
                effects=plan.get("effects"),
                source=prev_source,
                render_status="ok",
                extra={"broll_timings": "preflight"},
            )
            plan["clips"] = clips
    merged_effects = merge_render_effects(
        platform_id,
        plan.get("clips") or [],
        plan.get("effects"),
        use_remotion=cfg.render_use_remotion,
        feed_kind=str(brief.get("feed_kind") or "news"),
        bookends=cfg.render_bookends,
    )
    block: dict[str, Any] = {
        "clips": plan.get("clips") or [],
        "effects": merged_effects,
        "title": str(brief.get("title") or brief.get("hook") or ""),
    }
    if platform_id == "xhs":
        xhs_body = task_dir / "publish" / "xhs_body.txt"
        block["body"] = xhs_body.read_text(encoding="utf-8")[:500] if xhs_body.is_file() else " "
    ok, err = validate_platform_video_block(platform_id, block, broll_seconds=broll_sec)
    if not ok:
        raise ValueError(f"plan_preflight_failed:{platform_id}:{err}")
    out = task_dir / "videos" / f"{platform_id}.mp4"
    render_from_plan(
        clips=plan["clips"],
        broll_path=broll,
        output_path=str(out),
        platform=platform_id,
        max_seconds=preset.max_seconds,
        width=preset.width,
        height=preset.height,
        skip_tts=cfg.render_skip_tts,
        work_dir=str(task_dir / "videos" / f"_work_{platform_id}"),
        effects=plan.get("effects"),
        use_remotion=cfg.render_use_remotion,
        task_dir=str(task_dir),
        feed_kind=str(brief.get("feed_kind") or "news"),
        bookends=cfg.render_bookends,
        ffmpeg_preset=cfg.render_ffmpeg_preset,
    )
    return out


def _render_platform_job(cfg: PipelineConfig, task_dir: Path, platform_id: str) -> dict[str, Any]:
    preset = get_platform_preset(platform_id)
    path = render_from_llm_plan(cfg, task_dir, platform_id)
    return {"platform": platform_id, "label": preset.label, "path": str(path), "content_kind": "video"}


def _render_platforms_inner(
    cfg: PipelineConfig,
    task_dir: Path,
    presets: list,
) -> list[dict[str, Any]]:
    videos: list[dict[str, Any]] = []
    if cfg.render_parallel and len(presets) > 1:
        workers = min(cfg.render_parallel_workers, len(presets))
        errors: list[BaseException] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {
                pool.submit(_render_platform_job, cfg, task_dir, p.id): p for p in presets
            }
            for fut in as_completed(futs):
                try:
                    videos.append(fut.result())
                except BaseException as exc:
                    errors.append(exc)
        if errors:
            raise errors[0]
        videos.sort(key=lambda x: (0 if x["platform"] == "douyin" else 1, x["platform"]))
    else:
        for preset in presets:
            videos.append(_render_platform_job(cfg, task_dir, preset.id))
    return videos


def render_task_videos(
    cfg: PipelineConfig,
    task_dir: Path,
    *,
    platforms: list[str] | None = None,
) -> dict[str, Any] | None:
    if not cfg.render_enabled:
        return None

    from .slides_render import is_slides_render_mode, render_task_slides_videos

    if is_slides_render_mode(cfg):
        return render_task_slides_videos(cfg, task_dir, platforms=platforms)

    task_dir = task_dir.resolve()
    brief = load_brief(task_dir)
    presets = video_platforms(platforms or cfg.render_platforms)

    from .render_lock import global_render_slot

    with global_render_slot(cfg.data_dir, max_slots=cfg.render_max_concurrent):
        videos = _render_platforms_inner(cfg, task_dir, presets)

    articles = article_manifest_entries(task_dir)
    manifest = {
        "content_key": brief.get("content_key"),
        "article_id": brief.get("article_id"),
        "title": brief.get("title"),
        "videos": videos,
        "articles": articles,
        "executor": "python_agent.vsa_render.render_from_plan",
        "render_parallel": cfg.render_parallel,
    }
    manifest_path = task_dir / "videos" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    from .render_verify import run_post_render_verify

    verify_report = run_post_render_verify(
        task_dir,
        platforms=cfg.render_platforms,
        full_verify=cfg.render_full_verify,
    )
    if (
        cfg.render_enabled
        and cfg.render_verify_required
        and verify_report.get("ok") is not True
    ):
        raise RuntimeError(
            f"verify_failed: {json.dumps(verify_report, ensure_ascii=False)[:400]}"
        )

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
        "verify": verify_report,
    }
