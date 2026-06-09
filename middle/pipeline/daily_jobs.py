"""每日/随机定时：挑选待发布文章、补渲染、发布。"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .config import PipelineConfig
from .publish_picker import (
    collect_publish_candidates,
    pick_articles,
    random_gap_seconds,
    random_startup_delay_sec,
    video_ready,
)
from .schedule_config import ScheduleConfig


def pick_articles_to_publish(
    cfg: PipelineConfig,
    schedule: ScheduleConfig,
    *,
    count: int | None = None,
    mode: str | None = None,
) -> list[int]:
    """兼容旧接口：委托 publish_picker。"""
    return pick_articles(cfg, schedule, count=count, mode=mode)  # type: ignore[arg-type]


# 供外部引用
_video_ready = video_ready
collect_publish_candidates = collect_publish_candidates


def ensure_article_rendered(
    cfg: PipelineConfig,
    article_id: int,
    *,
    scripts_root: Path,
    python: str | None = None,
) -> bool:
    """缺成片时调用 refresh_copy_and_render。"""
    if video_ready(cfg, article_id, "douyin"):
        return True
    py = python or sys.executable
    cmd = [
        py,
        str(scripts_root / "refresh_copy_and_render.py"),
        "--article-id",
        str(article_id),
    ]
    r = subprocess.run(cmd, cwd=str(scripts_root.parent), capture_output=True, text=True)
    return r.returncode == 0 and video_ready(cfg, article_id, "douyin")


def publish_article_channels(
    cfg: PipelineConfig,
    article_id: int,
    channels: list[str],
    *,
    verify: bool,
    verify_wait_sec: int,
    note: str,
) -> dict[str, Any]:
    from publish_lib import (  # type: ignore[import-not-found]
        DEFAULT_ACCOUNTS,
        step_dry_run,
        step_mark,
        step_preflight,
        step_prepare,
        step_publish,
        step_verify,
        utc_now,
    )

    report: dict[str, Any] = {
        "article_id": article_id,
        "started_at": utc_now(),
        "channels": {},
        "ok": True,
    }
    for ch in channels:
        acc = DEFAULT_ACCOUNTS.get(ch, "")
        ch_out: dict[str, Any] = {"channel": ch}
        try:
            step_prepare(cfg, article_id, ch)
            step_preflight(cfg, article_id, ch, acc)
            if cfg.publish_require_dry_run:
                step_dry_run(cfg, article_id, ch, acc)
            step_publish(cfg, article_id, ch, acc, retries=2)
            if verify:
                time.sleep(verify_wait_sec)
                step_verify(cfg, article_id, ch, acc, retries=1)
            step_mark(cfg, article_id, ch, note)
            ch_out["ok"] = True
        except Exception as e:
            ch_out["ok"] = False
            ch_out["error"] = str(e)[:500]
            report["ok"] = False
        report["channels"][ch] = ch_out
        try:
            from publisher.browser_pool import get_pool

            get_pool(cfg.publisher).close_all()
        except Exception:
            pass
    report["finished_at"] = utc_now()
    return report


def check_publish_logins(scripts_root: Path, channels: list[str], *, python: str | None = None) -> bool:
    py = python or sys.executable
    r = subprocess.run(
        [py, str(scripts_root / "check_all_publish_logins.py"), "--json"],
        cwd=str(scripts_root.parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        return False
    try:
        data = json.loads(r.stdout)
        rows = data.get("channels") or []
        if not isinstance(rows, list):
            return r.returncode == 0
        need = set(channels)
        for row in rows:
            ch = row.get("channel")
            if ch in need and not row.get("logged_in"):
                return False
        checked = {row.get("channel") for row in rows if row.get("channel") in need}
        return need <= checked and all(
            row.get("logged_in") for row in rows if row.get("channel") in need
        )
    except Exception:
        return r.returncode == 0


def write_schedule_log(log_path: Path, payload: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sleep_random_gap(schedule: ScheduleConfig) -> int:
    """篇间随机等待，返回实际秒数。"""
    sec = random_gap_seconds(schedule)
    if sec > 0:
        time.sleep(sec)
    return sec


def sleep_random_startup(schedule: ScheduleConfig) -> int:
    """任务启动前随机等待，返回实际秒数。"""
    sec = random_startup_delay_sec(schedule)
    if sec > 0:
        time.sleep(sec)
    return sec
