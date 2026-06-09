"""定时发布周期（供 CLI 与 schedule_service 共用）。"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import PipelineConfig
from .daily_jobs import (
    check_publish_logins,
    ensure_article_rendered,
    publish_article_channels,
    sleep_random_gap,
    sleep_random_startup,
    write_schedule_log,
)
from .orchestrator import run_pipeline
from .publish_picker import collect_publish_candidates, pick_articles, resolve_daily_publish_count
from .schedule_config import ScheduleConfig


@dataclass
class ScheduleRunOptions:
    pipeline_only: bool = False
    publish_only: bool = False
    skip_startup_delay: bool = False
    skip_gap: bool = False
    skip_login_check: bool = False
    count_override: int | None = None
    force_pick_mode: str | None = None
    note: str = "schedule_runner"


def _scripts_root(middle_root: Path) -> Path:
    return middle_root / "scripts"


def run_publish_cycle(
    cfg: PipelineConfig,
    schedule: ScheduleConfig,
    *,
    middle_root: Path,
    options: ScheduleRunOptions | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """执行一轮：可选 pipeline → 选文 → 发布。返回汇总 dict（含 ok）。"""
    opt = options or ScheduleRunOptions()
    if not schedule.enabled:
        return {"ok": True, "skipped": True, "reason": "schedule_disabled"}

    channels = schedule.effective_channels()
    if not channels and not opt.pipeline_only:
        return {"ok": False, "error": "no_channels"}

    rng = rng or random.Random(schedule.random_seed)
    sched = schedule
    if opt.force_pick_mode:
        sched.pick_mode = opt.force_pick_mode

    count = resolve_daily_publish_count(sched, override=opt.count_override, rng=rng)
    log_dir = Path(schedule.log_dir)
    if not log_dir.is_absolute():
        log_dir = middle_root / log_dir
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    task = "service" if opt.note.startswith("schedule_service") else "random"
    log_path = log_dir / f"{task}_{day}.json"

    summary: dict[str, Any] = {
        "task": task,
        "note": opt.note,
        "started_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "pick_mode": sched.pick_mode,
        "daily_publish_count": count,
        "channels": channels,
        "articles": [],
        "ok": True,
    }

    if not opt.publish_only and not opt.skip_startup_delay:
        delay = sleep_random_startup(sched)
        if delay:
            summary["startup_delay_sec"] = delay

    if not opt.publish_only and sched.run_pipeline:
        stats = run_pipeline(cfg, max_jobs=sched.max_pipeline_jobs)
        summary["pipeline"] = {
            "discovered": stats.discovered,
            "packed": stats.packed,
            "rendered": stats.rendered,
            "skipped": stats.skipped,
            "failed": stats.failed,
            "errors": stats.errors[:20],
        }

    if opt.pipeline_only:
        write_schedule_log(log_path, summary)
        return summary

    if not sched.auto_publish and not opt.publish_only:
        summary["publish_skipped"] = "auto_publish_disabled"
        summary["message"] = "自动发布已关闭，请用手动 publish_channel.py"
        write_schedule_log(log_path, summary)
        return summary

    pool = collect_publish_candidates(cfg, sched)
    summary["candidate_pool_size"] = len(pool)
    article_ids = pick_articles(cfg, sched, count=count, mode=sched.pick_mode, rng=rng)
    summary["picked_article_ids"] = article_ids

    if not article_ids:
        summary["message"] = "no_candidates"
        write_schedule_log(log_path, summary)
        return summary

    scripts = _scripts_root(middle_root)
    if sched.login_check and not opt.skip_login_check:
        if not check_publish_logins(scripts, channels):
            summary["ok"] = False
            summary["error"] = "publish_login_required"
            write_schedule_log(log_path, summary)
            return summary

    for i, aid in enumerate(article_ids):
        if i > 0 and not opt.skip_gap:
            gap = sleep_random_gap(sched)
            if gap:
                summary.setdefault("gaps_sec", []).append(gap)

        art_log: dict[str, Any] = {"article_id": aid}
        video = cfg.output_root / str(aid) / "videos" / "douyin.mp4"
        if not video.is_file():
            ok_render = ensure_article_rendered(cfg, aid, scripts_root=scripts)
            art_log["render_attempt"] = ok_render
            if not ok_render:
                art_log["ok"] = False
                art_log["error"] = "render_failed"
                summary["articles"].append(art_log)
                summary["ok"] = False
                continue

        pub = publish_article_channels(
            cfg,
            aid,
            channels,
            verify=sched.publish_verify,
            verify_wait_sec=sched.verify_wait_sec,
            note=opt.note,
        )
        art_log["publish"] = pub
        art_log["ok"] = pub.get("ok", False)
        if not art_log["ok"]:
            summary["ok"] = False
        summary["articles"].append(art_log)

    summary["finished_at"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_schedule_log(log_path, summary)
    return summary
