"""自动发布开关。"""
from __future__ import annotations

from pipeline.schedule_config import parse_schedule_config
from pipeline.schedule_runner import ScheduleRunOptions, run_publish_cycle
from pipeline.config import PipelineConfig
from pathlib import Path


def test_parse_auto_publish_default_false() -> None:
    sched = parse_schedule_config({})
    assert sched.auto_publish is False


def test_run_publish_cycle_skips_when_auto_publish_off(tmp_path: Path) -> None:
    cfg = PipelineConfig(data_dir=tmp_path / "data")
    sched = parse_schedule_config({"enabled": True, "auto_publish": False, "channels": ["douyin"]})
    summary = run_publish_cycle(
        cfg,
        sched,
        middle_root=tmp_path,
        options=ScheduleRunOptions(note="test"),
    )
    assert summary.get("publish_skipped") == "auto_publish_disabled"
