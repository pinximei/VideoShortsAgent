"""待发布文章挑选：顺序 / 随机。"""
from __future__ import annotations

import random
from typing import Literal

from .config import PipelineConfig
from .db import JobStore
from .pipeline_gates import gate_summary
from .platform_presets import get_platform_preset
from .schedule_config import ScheduleConfig

PickMode = Literal["fifo", "random", "newest"]


def video_ready(cfg: PipelineConfig, article_id: int, channel: str) -> bool:
    task = cfg.output_root / str(article_id)
    preset = get_platform_preset(channel)
    if preset.content_kind == "video":
        name = "douyin.mp4" if channel == "douyin" else f"{channel}.mp4"
        return (task / "videos" / name).is_file()
    txt = {"toutiao": "toutiao_micro.txt", "douban": "douban_note.txt"}.get(channel)
    return bool(txt and (task / "publish" / txt).is_file())


def collect_publish_candidates(
    cfg: PipelineConfig,
    schedule: ScheduleConfig,
) -> list[int]:
    """所有可发布候选 article_id（主渠道未 mark、有成片、门禁通过）。"""
    store = JobStore(cfg.db_path)
    pending = store.pending_publish(
        schedule.primary_channel,
        theme_id=schedule.theme_id or None,
    )
    candidates: list[int] = []
    seen: set[int] = set()
    for job in pending:
        aid = int(job["article_id"])
        if aid in seen:
            continue
        seen.add(aid)
        task = cfg.output_root / str(aid)
        if not (task / "brief.json").is_file():
            continue
        if not video_ready(cfg, aid, schedule.primary_channel):
            continue
        if cfg.pipeline_fail_closed:
            summary = gate_summary(task, cfg)
            if not summary.get("ok"):
                continue
        candidates.append(aid)
    return candidates


def resolve_daily_publish_count(
    schedule: ScheduleConfig,
    *,
    override: int | None = None,
    rng: random.Random | None = None,
) -> int:
    """解析本轮发布篇数：固定值或 [min,max] 随机。"""
    if override and override > 0:
        return max(1, min(override, 10))
    lo = schedule.daily_publish_count_min
    hi = schedule.daily_publish_count_max
    if lo is not None and hi is not None and hi >= lo:
        r = rng or random.Random()
        return r.randint(int(lo), int(hi))
    return schedule.daily_publish_count


def pick_articles(
    cfg: PipelineConfig,
    schedule: ScheduleConfig,
    *,
    count: int | None = None,
    mode: PickMode | None = None,
    rng: random.Random | None = None,
) -> list[int]:
    """按策略从候选池挑选待发布文章。"""
    n = resolve_daily_publish_count(schedule, override=count, rng=rng)
    pool = collect_publish_candidates(cfg, schedule)
    if not pool:
        return []

    pick = (mode or schedule.pick_mode or "fifo").strip().lower()
    r = rng or random.Random(schedule.random_seed)

    if pick == "random":
        k = min(n, len(pool))
        return r.sample(pool, k)

    if pick == "newest":
        ordered = sorted(pool, reverse=True)
        return ordered[:n]

    # fifo：保持 DB 返回顺序（通常 updated_at DESC）
    return pool[:n]


def random_gap_seconds(schedule: ScheduleConfig, rng: random.Random | None = None) -> int:
    """两篇之间的随机间隔秒数；未配置则 0。"""
    lo = schedule.gap_between_articles_sec_min
    hi = schedule.gap_between_articles_sec_max
    if lo is None or hi is None or hi <= 0:
        return 0
    lo = max(0, int(lo))
    hi = max(lo, int(hi))
    if hi == 0:
        return 0
    r = rng or random.Random()
    return r.randint(lo, hi)


def random_startup_delay_sec(schedule: ScheduleConfig, rng: random.Random | None = None) -> int:
    """任务启动前随机等待（用于错开发布时刻）。"""
    lo = schedule.random_start_delay_sec_min
    hi = schedule.random_start_delay_sec_max
    if lo is None or hi is None or hi <= 0:
        return 0
    lo = max(0, int(lo))
    hi = max(lo, int(hi))
    r = rng or random.Random()
    return r.randint(lo, hi)
