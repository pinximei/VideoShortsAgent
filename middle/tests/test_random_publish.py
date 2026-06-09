"""随机发布挑选。"""
from __future__ import annotations

import random
from pathlib import Path

from pipeline.config import PipelineConfig
from pipeline.db import JobStore
from pipeline.models import content_key_for_article
from pipeline.publish_picker import collect_publish_candidates, pick_articles, resolve_daily_publish_count
from pipeline.schedule_config import ScheduleConfig, parse_schedule_config


def _seed_job(data: Path, article_id: int) -> None:
    out = data / "output" / str(article_id)
    (out / "videos").mkdir(parents=True, exist_ok=True)
    (out / "videos" / "douyin.mp4").write_bytes(b"x" * 80_000)
    (out / "brief.json").write_text(
        f'{{"theme_id":"ai_news","title":"a{article_id}"}}',
        encoding="utf-8",
    )


def test_resolve_random_count_range() -> None:
    s = ScheduleConfig(daily_publish_count_min=2, daily_publish_count_max=3)
    rng = random.Random(99)
    for _ in range(20):
        n = resolve_daily_publish_count(s, rng=rng)
        assert 2 <= n <= 3


def test_pick_random_subset(tmp_path: Path) -> None:
    data = tmp_path / "data"
    cfg = PipelineConfig(
        data_dir=data,
        render_enabled=True,
        pipeline_fail_closed=False,
    )
    store = JobStore(cfg.db_path)
    for aid in (201, 202, 203, 204, 205):
        _seed_job(data, aid)
        ck = content_key_for_article(aid)
        store.upsert_discovered(
            content_key=ck, article_id=aid, snapshot={"id": aid}, theme_id="ai_news"
        )
        store.advance(ck, status="ready_to_publish", step="ready", theme_id="ai_news")

    sched = ScheduleConfig(
        daily_publish_count=2,
        pick_mode="random",
        theme_id="ai_news",
        primary_channel="douyin",
    )
    pool = collect_publish_candidates(cfg, sched)
    assert len(pool) == 5
    rng = random.Random(7)
    picked = pick_articles(cfg, sched, count=2, mode="random", rng=rng)
    assert len(picked) == 2
    assert set(picked) <= set(pool)
    assert pick_articles(cfg, sched, count=2, mode="random", rng=random.Random(7)) == picked


def test_parse_schedule_random_mode() -> None:
    s = parse_schedule_config(
        {
            "pick_mode": "random",
            "daily_publish_count_min": 2,
            "daily_publish_count_max": 3,
            "gap_between_articles_sec": [60, 120],
        }
    )
    assert s.pick_mode == "random"
    assert s.daily_publish_count_min == 2
    assert s.gap_between_articles_sec_min == 60
    assert s.gap_between_articles_sec_max == 120
