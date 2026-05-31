from __future__ import annotations

import json
from pathlib import Path

from .brief import build_brief, brief_is_renderable, passes_filter
from .article_content import article_has_substantive_content, collect_article_text, content_quality_report
from .themes import resolve_theme
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
from .publish_guard import PublishGuardError, build_publish_bindings
from .soul_client import SoulClient
from .pipeline_gates import PipelineGateError, assert_task_ready_for_publish
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

            content_ok, content_reason = article_has_substantive_content(article)
            if not content_ok:
                store.advance(ck, status=STATUS_SKIPPED, step=STEP_FILTER, message=content_reason)
                stats.skipped += 1
                continue

            theme_id = resolve_theme(article, cfg.themes)
            if not theme_id:
                store.advance(ck, status=STATUS_SKIPPED, step=STEP_FILTER, message="no matching theme")
                stats.skipped += 1
                continue

            store.advance(ck, status=STATUS_PROCESSING, step=STEP_BRIEF, theme_id=theme_id)
            brief = build_brief(article, public_base_url=cfg.public_base_url, theme_id=theme_id)
            brief_ok, brief_reason = brief_is_renderable(brief)
            if not brief_ok:
                store.advance(ck, status=STATUS_SKIPPED, step=STEP_BRIEF, message=brief_reason)
                stats.skipped += 1
                continue
            bh = brief.hash()

            if store.should_skip_render(ck, bh):
                stats.deduped += 1
                continue

            out_dir = cfg.output_root / str(article_id)
            out_dir.mkdir(parents=True, exist_ok=True)
            brief_dict = brief.to_dict()
            if brief.cover_image_url:
                from python_agent.pipeline_media import prefetch_task_cover

                prefetch_task_cover(out_dir, brief_dict)
            store.advance(
                ck,
                status=STATUS_PROCESSING,
                step=STEP_BRIEF,
                brief_hash=bh,
                brief_json=brief_dict,
                output_dir=str(out_dir),
                message=f"正文 {content_quality_report(article)['substantive_chars']} 字",
            )
            stats.queued += 1

            broll_sec = probe_video_duration(cfg.broll_template) if cfg.broll_template else None

            excerpt_path = out_dir / "source_excerpt.txt"
            excerpt_path.write_text(
                collect_article_text(article, max_chars=8000),
                encoding="utf-8",
            )

            store.advance(ck, status=STATUS_PROCESSING, step=STEP_LLM, message="大模型生成各平台文案与分镜")
            pack_meta = write_publish_pack(brief, out_dir, cfg=cfg, article=article, broll_seconds=broll_sec)
            store.advance(ck, status=STATUS_PROCESSING, step=STEP_PACK, message="发布包已写入")
            if cfg.render_enabled and cfg.pipeline_fail_closed:
                from .pipeline_gates import assert_publish_pack_meta, assert_video_plans

                assert_publish_pack_meta(out_dir, cfg)
                assert_video_plans(out_dir, cfg)

            if cfg.render_enabled:
                from .render_verify import run_post_render_verify

                store.advance(ck, status=STATUS_PROCESSING, step=STEP_VSA, message="VSA 裁剪视频")
                verify_report: dict | None = None
                last_render_err: str | None = None
                attempts = cfg.render_retry_max + 1
                for attempt in range(attempts):
                    try:
                        result = render_task_videos(cfg, out_dir)
                        if not result or not result.get("primary_video"):
                            raise RuntimeError("VSA 未产出视频")
                        verify_report = run_post_render_verify(
                            out_dir,
                            platforms=cfg.render_platforms,
                            full_verify=cfg.render_full_verify,
                        )
                        if cfg.pipeline_fail_closed:
                            if verify_report.get("ok") is not True:
                                last_render_err = json.dumps(
                                    verify_report, ensure_ascii=False
                                )[:400]
                            else:
                                last_render_err = None
                                break
                        elif verify_report.get("ok") is True or not cfg.render_verify_required:
                            last_render_err = None
                            break
                        else:
                            last_render_err = json.dumps(
                                verify_report, ensure_ascii=False
                            )[:400]
                    except Exception as rexc:
                        last_render_err = f"{type(rexc).__name__}: {str(rexc)[:200]}"
                    if attempt < attempts - 1:
                        store.advance(
                            ck,
                            status=STATUS_PROCESSING,
                            step=STEP_VSA,
                            message=f"渲染/验收失败，重试 ({attempt + 2}/{attempts})",
                        )
                if last_render_err:
                    raise RuntimeError(f"render_failed: {last_render_err}")

            brief_dict = brief.to_dict()
            brief_dict["publish_bindings"] = build_publish_bindings(cfg, theme_id)

            assert_task_ready_for_publish(
                cfg,
                out_dir,
                brief_dict=brief_dict,
                strict=True if cfg.pipeline_fail_closed else None,
            )
            brief_dict["pipeline_gate"] = {"ok": True, "at": "ready"}

            store.advance(
                ck,
                status=STATUS_READY,
                step=STEP_READY,
                message="内容就绪，请在各平台发布后标记",
                brief_json=brief_dict,
            )
            stats.packed += 1
            if cfg.render_enabled:
                stats.rendered += 1
        except (PipelineGateError, PublishGuardError) as e:
            code = getattr(e, "code", type(e).__name__)
            msg = getattr(e, "message", str(e))[:240]
            store.advance(ck, status=STATUS_FAILED, step=job.get("step") or "gate", error=f"{code}: {msg}")
            stats.failed += 1
            stats.errors.append(f"{ck}: {code}: {msg}")
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
