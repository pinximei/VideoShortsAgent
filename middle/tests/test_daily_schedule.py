"""每日定时挑选逻辑。"""
from __future__ import annotations

from pathlib import Path

from pipeline.config import PipelineConfig
from pipeline.daily_jobs import pick_articles_to_publish
from pipeline.db import JobStore
from pipeline.models import content_key_for_article
from pipeline.schedule_config import ScheduleConfig, parse_schedule_config


def test_parse_schedule_defaults() -> None:
    s = parse_schedule_config({})
    assert s.daily_publish_count == 3
    assert "xhs" in s.skip_channels
    assert s.effective_channels() == ["douyin", "toutiao", "douban"]


def test_pick_articles_pending_primary(tmp_path: Path) -> None:
    data = tmp_path / "data"
    out = data / "output" / "101"
    (out / "videos").mkdir(parents=True)
    (out / "videos" / "douyin.mp4").write_bytes(b"x" * 100_000)
    (out / "brief.json").write_text(
        '{"theme_id":"ai_news","title":"t"}',
        encoding="utf-8",
    )
    (out / "publish_meta.json").write_text(
        '{"source":"llm","video_plans":["douyin"]}',
        encoding="utf-8",
    )
    (out / "verify_report.json").write_text('{"ok":true}', encoding="utf-8")

    cfg = PipelineConfig(
        data_dir=data,
        render_enabled=True,
        feed_kinds=["news"],
        pipeline_fail_closed=False,
    )
    store = JobStore(cfg.db_path)
    ck = content_key_for_article(101)
    store.upsert_discovered(content_key=ck, article_id=101, snapshot={"id": 101}, theme_id="ai_news")
    store.advance(ck, status="ready_to_publish", step="ready", theme_id="ai_news")

    sched = ScheduleConfig(daily_publish_count=2, theme_id="ai_news", primary_channel="douyin")
    picked = pick_articles_to_publish(cfg, sched, count=2)
    assert picked == [101]
