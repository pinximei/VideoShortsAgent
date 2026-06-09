"""定时发布配置（config.yaml → schedule）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScheduleConfig:
    enabled: bool = True
    daily_publish_count: int = 3
    daily_publish_count_min: int | None = None
    daily_publish_count_max: int | None = None
    pick_mode: str = "fifo"
    random_seed: int | None = None
    max_pipeline_jobs: int = 5
    theme_id: str = "ai_news"
    primary_channel: str = "douyin"
    channels: list[str] = field(
        default_factory=lambda: ["douyin", "toutiao", "douban"]
    )
    skip_channels: list[str] = field(default_factory=lambda: ["xhs"])
    run_pipeline: bool = True
    """为 false 时调度/定时任务只拉稿成片，不调用浏览器发布（需手动 publish_channel.py）。"""
    auto_publish: bool = False
    publish_verify: bool = True
    login_check: bool = True
    verify_wait_sec: int = 25
    gap_between_articles_sec_min: int | None = None
    gap_between_articles_sec_max: int | None = None
    random_start_delay_sec_min: int | None = None
    random_start_delay_sec_max: int | None = None
    log_dir: str = "./data/logs/schedule"

    def effective_channels(self) -> list[str]:
        skip = set(self.skip_channels or [])
        out: list[str] = []
        for ch in self.channels:
            c = str(ch).strip()
            if c and c not in skip and c not in out:
                out.append(c)
        return out


def parse_schedule_config(raw: dict[str, Any] | None) -> ScheduleConfig:
    s = raw or {}
    channels = s.get("channels") or ["douyin", "toutiao", "douban"]
    if isinstance(channels, str):
        channels = [c.strip() for c in channels.split(",") if c.strip()]
    skip = s.get("skip_channels") or ["xhs"]
    if isinstance(skip, str):
        skip = [c.strip() for c in skip.split(",") if c.strip()]
    count = int(s.get("daily_publish_count") or s.get("daily_count") or 3)
    count = max(1, min(count, 10))
    cmin = s.get("daily_publish_count_min")
    cmax = s.get("daily_publish_count_max")
    cmin_i = int(cmin) if cmin is not None else None
    cmax_i = int(cmax) if cmax is not None else None
    pick_mode = str(s.get("pick_mode") or "fifo").strip().lower() or "fifo"
    seed_raw = s.get("random_seed")
    random_seed = int(seed_raw) if seed_raw is not None and str(seed_raw).strip() != "" else None

    def _pair_min(name_min: str, name_max: str) -> tuple[int | None, int | None]:
        a, b = s.get(name_min), s.get(name_max)
        if a is None and b is None:
            gap = s.get("gap_between_articles_sec")
            if name_min.startswith("gap") and isinstance(gap, (list, tuple)) and len(gap) >= 2:
                return int(gap[0]), int(gap[1])
            start = s.get("random_start_delay_sec")
            if name_min.startswith("random_start") and isinstance(start, (list, tuple)) and len(start) >= 2:
                return int(start[0]), int(start[1])
            return None, None
        return (
            int(a) if a is not None else None,
            int(b) if b is not None else None,
        )

    gap_lo, gap_hi = _pair_min("gap_between_articles_sec_min", "gap_between_articles_sec_max")
    start_lo, start_hi = _pair_min(
        "random_start_delay_sec_min", "random_start_delay_sec_max"
    )

    return ScheduleConfig(
        enabled=bool(s.get("enabled", True)),
        daily_publish_count=count,
        daily_publish_count_min=cmin_i,
        daily_publish_count_max=cmax_i,
        pick_mode=pick_mode,
        random_seed=random_seed,
        max_pipeline_jobs=max(1, int(s.get("max_pipeline_jobs") or count + 2)),
        theme_id=str(s.get("theme_id") or "ai_news").strip() or "ai_news",
        primary_channel=str(s.get("primary_channel") or "douyin").strip() or "douyin",
        channels=[str(c).strip() for c in channels if str(c).strip()],
        skip_channels=[str(c).strip() for c in skip if str(c).strip()],
        run_pipeline=bool(s.get("run_pipeline", True)),
        auto_publish=bool(s.get("auto_publish", False)),
        publish_verify=bool(s.get("publish_verify", True)),
        login_check=bool(s.get("login_check", True)),
        verify_wait_sec=max(5, int(s.get("verify_wait_sec") or 25)),
        gap_between_articles_sec_min=gap_lo,
        gap_between_articles_sec_max=gap_hi,
        random_start_delay_sec_min=start_lo,
        random_start_delay_sec_max=start_hi,
        log_dir=str(s.get("log_dir") or "./data/logs/schedule"),
    )
