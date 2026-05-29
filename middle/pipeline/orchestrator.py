from __future__ import annotations

from pathlib import Path

from .brief import build_brief, passes_filter
from .config import PipelineConfig
from .db import JobStore
from .discover import discover_from_soul
from .job_flow import (
    STEP_BRIEF,
    STEP_FETCH,
    STEP_FILTER,
    STEP_LLM,
    STEP_PACK,
    STEP_READY,
    STEP_VSA,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STATUS_READY,
    STATUS_SKIPPED,
)
from .media_probe import probe_video_duration
from .models import RunStats
from .platform_llm import write_publish_pack
from .soul_client import SoulClient
from .vsa import render_task_videos


def process_jobs(
    cfg: PipelineConfig,
    store: JobStore,
    soul: SoulClient | None = None,
) -> RunStats:
    stats = RunStats()
    client = soul or SoulClient(cfg)
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.output_root.mkdir(parents=True, exist_ok=True)

    jobs = store.list_jobs((STATUS_PROCESSING, "discovered", "queued", "failed"))
    for job in jobs:
        ck = job["content_key"]
        article_id = int(job["article_id"])
        try:
            store.advance(ck, status=STATUS_PROCESSING, step=STEP_FETCH, message="拉取 Soul 文章")
            article = client.get_article(article_id)
            if not article:
                store.advance(ck, status=STATUS_FAILED, step=STEP_FETCH, error="article not found")
                stats.failed += 1
                continue

            store.advance(ck, status=STATUS_PROCESSING, step=STEP_FILTER)
            ok, reason = passes_filter(
                article,
                min_worth=cfg.min_worth_score,
                feed_kinds=cfg.feed_kinds,
            )
            if not ok:
                store.advance(ck, status=STATUS_SKIPPED, step=STEP_FILTER, message=reason)
                stats.skipped += 1
                continue

            store.advance(ck, status=STATUS_PROCESSING, step=STEP_BRIEF)
            brief = build_brief(article, public_base_url=cfg.public_base_url)
            bh = brief.hash()

            if store.should_skip_render(ck, bh):
                stats.deduped += 1
                continue

            out_dir = cfg.output_root / str(article_id)
            store.advance(
                ck,
                status=STATUS_PROCESSING,
                step=STEP_BRIEF,
                brief_hash=bh,
                brief_json=brief.to_dict(),
                output_dir=str(out_dir),
            )
            stats.queued += 1

            broll_sec = probe_video_duration(cfg.broll_template) if cfg.broll_template else None

            store.advance(ck, status=STATUS_PROCESSING, step=STEP_LLM, message="大模型生成各平台文案与分镜")
            write_publish_pack(brief, out_dir, cfg=cfg, article=article, broll_seconds=broll_sec)
            store.advance(ck, status=STATUS_PROCESSING, step=STEP_PACK, message="发布包已写入")

            if cfg.render_enabled:
                store.advance(ck, status=STATUS_PROCESSING, step=STEP_VSA, message="VSA 裁剪视频")
                result = render_task_videos(cfg, out_dir)
                if not result or not result.get("primary_video"):
                    raise RuntimeError("VSA 未产出视频")

            store.advance(
                ck,
                status=STATUS_READY,
                step=STEP_READY,
                message="内容就绪，请在各平台发布后标记",
            )
            stats.packed += 1
            if cfg.render_enabled:
                stats.rendered += 1
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:240]}"
            store.advance(ck, status=STATUS_FAILED, step=job.get("step") or "error", error=err)
            stats.failed += 1
            stats.errors.append(f"{ck}: {err}")

    return stats


def run_pipeline(cfg: PipelineConfig, soul: SoulClient | None = None) -> RunStats:
    store = JobStore(cfg.db_path)
    total = RunStats()
    d = discover_from_soul(cfg, store, soul=soul)
    total.discovered = d.discovered
    total.deduped = d.deduped
    p = process_jobs(cfg, store, soul=soul)
    total.skipped = p.skipped
    total.queued = p.queued
    total.rendered = p.rendered
    total.packed = p.packed
    total.failed = p.failed
    total.deduped += p.deduped
    total.errors = p.errors
    return total
