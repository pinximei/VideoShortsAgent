"""内置调度服务逻辑。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pipeline.config import PipelineConfig
from pipeline.schedule_service import (
    ScheduleServiceState,
    pipeline_due,
    publish_due,
    save_service_state,
    load_service_state,
)


def test_pipeline_due_when_never_ran() -> None:
    assert pipeline_due(ScheduleServiceState(), interval_min=30, tz_name="Asia/Shanghai")


def test_publish_due_after_hour(tmp_path: Path) -> None:
    cfg = PipelineConfig(data_dir=tmp_path / "data")
    state = ScheduleServiceState(last_publish_day="19990101")
    assert publish_due(state, publish_hour_local=0, tz_name="Asia/Shanghai")


def test_publish_not_due_same_day() -> None:
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
    state = ScheduleServiceState(last_publish_day=today)
    assert not publish_due(state, publish_hour_local=0, tz_name="Asia/Shanghai")


def test_state_roundtrip(tmp_path: Path) -> None:
    cfg = PipelineConfig(data_dir=tmp_path / "data")
    st = ScheduleServiceState(last_pipeline_at="2026-05-24T10:00:00+08:00", cycles=3)
    save_service_state(cfg, st)
    loaded = load_service_state(cfg)
    assert loaded.cycles == 3
    assert loaded.last_pipeline_at == st.last_pipeline_at
