"""中间层内置 7×24 调度：随 API 服务启动，不依赖 Windows 计划任务。"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from .config import PipelineConfig
from .models import RunStats
from .schedule_config import ScheduleConfig, parse_schedule_config
from .run_lock import record_run, release_run, try_acquire_run
from .schedule_runner import ScheduleRunOptions, run_publish_cycle

logger = logging.getLogger("schedule_service")

_MIDDLE_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ScheduleServiceState:
    last_pipeline_at: str | None = None
    last_publish_day: str | None = None
    last_publish_at: str | None = None
    last_publish_ok: bool | None = None
    last_error: str | None = None
    cycles: int = 0


@dataclass
class ScheduleServiceStatus:
    running: bool = False
    enabled: bool = False
    auto_publish: bool = False
    pipeline_interval_min: int = 30
    publish_hour_local: int = 10
    timezone: str = "Asia/Shanghai"
    state: ScheduleServiceState = field(default_factory=ScheduleServiceState)
    last_wake_at: str | None = None
    next_pipeline_at: str | None = None
    next_publish_window: str | None = None


def _load_schedule_raw(cfg: PipelineConfig) -> dict[str, Any]:
    path = cfg.config_path
    if path and path.is_file():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return raw.get("schedule") or {}
    return {}


def _state_path(cfg: PipelineConfig) -> Path:
    return cfg.data_dir / "schedule_service_state.json"


def load_service_state(cfg: PipelineConfig) -> ScheduleServiceState:
    path = _state_path(cfg)
    if not path.is_file():
        return ScheduleServiceState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ScheduleServiceState(
            last_pipeline_at=data.get("last_pipeline_at"),
            last_publish_day=data.get("last_publish_day"),
            last_publish_at=data.get("last_publish_at"),
            last_publish_ok=data.get("last_publish_ok"),
            last_error=data.get("last_error"),
            cycles=int(data.get("cycles") or 0),
        )
    except Exception:
        return ScheduleServiceState()


def save_service_state(cfg: PipelineConfig, state: ScheduleServiceState) -> None:
    path = _state_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")


def _now_local(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))


def pipeline_due(
    state: ScheduleServiceState,
    *,
    interval_min: int,
    tz_name: str,
) -> bool:
    if not state.last_pipeline_at:
        return True
    try:
        last = datetime.fromisoformat(state.last_pipeline_at)
        if last.tzinfo is None:
            last = last.replace(tzinfo=ZoneInfo(tz_name))
    except Exception:
        return True
    elapsed = (_now_local(tz_name) - last.astimezone(ZoneInfo(tz_name))).total_seconds()
    return elapsed >= max(1, interval_min) * 60


def publish_due(
    state: ScheduleServiceState,
    *,
    publish_hour_local: int,
    tz_name: str,
) -> bool:
    now = _now_local(tz_name)
    today = now.strftime("%Y%m%d")
    if state.last_publish_day == today:
        return False
    hour = max(0, min(23, int(publish_hour_local)))
    return now.hour >= hour


class BackgroundScheduleService:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._status = ScheduleServiceStatus()
        self._cfg_loader: Callable[[], PipelineConfig] | None = None

    def status(self) -> dict[str, Any]:
        with self._lock:
            return asdict(self._status)

    def start(self, cfg_loader: Callable[[], PipelineConfig]) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._cfg_loader = cfg_loader
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop,
                name="middle-schedule-service",
                daemon=True,
            )
            self._thread.start()
            self._status.running = True

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            self._status.running = False

    def _parse(self, cfg: PipelineConfig) -> ScheduleConfig:
        return parse_schedule_config(_load_schedule_raw(cfg))

    def _tick(self, cfg: PipelineConfig) -> None:
        sched = self._parse(cfg)
        raw = _load_schedule_raw(cfg)
        svc = raw.get("service") if isinstance(raw.get("service"), dict) else {}
        if not sched.enabled or not bool(svc.get("enabled", True)):
            with self._lock:
                self._status.enabled = False
            return

        interval_min = max(5, int(svc.get("pipeline_interval_min") or 30))
        publish_hour = int(svc.get("publish_hour_local") or 10)
        tz_name = str(svc.get("timezone") or "Asia/Shanghai").strip() or "Asia/Shanghai"

        state = load_service_state(cfg)
        now_local = _now_local(tz_name)

        with self._lock:
            self._status.enabled = True
            self._status.auto_publish = sched.auto_publish
            self._status.pipeline_interval_min = interval_min
            self._status.publish_hour_local = publish_hour
            self._status.timezone = tz_name
            self._status.state = state
            self._status.last_wake_at = now_local.isoformat()

        if pipeline_due(state, interval_min=interval_min, tz_name=tz_name):
            self._run_pipeline(cfg, sched, state)

        state = load_service_state(cfg)
        if sched.auto_publish and publish_due(
            state,
            publish_hour_local=publish_hour,
            tz_name=tz_name,
        ):
            self._run_publish(cfg, sched, state, tz_name)

    def _service_tz(self, cfg: PipelineConfig) -> str:
        raw = _load_schedule_raw(cfg)
        svc = raw.get("service") if isinstance(raw.get("service"), dict) else {}
        return str(svc.get("timezone") or "Asia/Shanghai").strip() or "Asia/Shanghai"

    def _run_pipeline(
        self,
        cfg: PipelineConfig,
        sched: ScheduleConfig,
        state: ScheduleServiceState,
    ) -> None:
        if not sched.run_pipeline:
            return
        if not try_acquire_run():
            logger.info("pipeline skipped: another run in progress")
            return
        tz = self._service_tz(cfg)
        try:
            from .orchestrator import run_pipeline

            stats = run_pipeline(cfg, max_jobs=sched.max_pipeline_jobs)
            record_run(stats)
            state.last_pipeline_at = _now_local(tz).isoformat()
            state.last_error = None
            state.cycles += 1
            save_service_state(cfg, state)
            logger.info(
                "pipeline tick: discovered=%s packed=%s failed=%s",
                stats.discovered,
                stats.packed,
                stats.failed,
            )
        except Exception as e:
            state.last_error = f"pipeline:{type(e).__name__}:{e}"[:300]
            save_service_state(cfg, state)
            record_run(RunStats(), error=state.last_error)
            logger.exception("pipeline tick failed")
        finally:
            release_run()

    def _run_publish(
        self,
        cfg: PipelineConfig,
        sched: ScheduleConfig,
        state: ScheduleServiceState,
        tz_name: str,
    ) -> None:
        if not try_acquire_run():
            logger.info("publish cycle skipped: another run in progress")
            return
        try:
            summary = run_publish_cycle(
                cfg,
                sched,
                middle_root=_MIDDLE_ROOT,
                options=ScheduleRunOptions(note="schedule_service"),
            )
            today = _now_local(tz_name).strftime("%Y%m%d")
            state.last_publish_day = today
            state.last_publish_at = _now_local(tz_name).isoformat()
            state.last_publish_ok = bool(summary.get("ok", False))
            state.last_error = None if state.last_publish_ok else str(summary.get("error") or "publish_failed")[:300]
            state.cycles += 1
            save_service_state(cfg, state)
            logger.info(
                "publish cycle done: ok=%s picked=%s",
                state.last_publish_ok,
                summary.get("picked_article_ids"),
            )
        except Exception as e:
            state.last_error = f"publish:{type(e).__name__}:{e}"[:300]
            save_service_state(cfg, state)
            logger.exception("publish cycle failed")
        finally:
            release_run()

    def _loop(self) -> None:
        logger.info("schedule service started")
        while not self._stop.is_set():
            try:
                if self._cfg_loader:
                    self._tick(self._cfg_loader())
            except Exception:
                logger.exception("schedule tick error")
            self._stop.wait(60)
        logger.info("schedule service stopped")


_service: BackgroundScheduleService | None = None


def get_schedule_service() -> BackgroundScheduleService:
    global _service
    if _service is None:
        _service = BackgroundScheduleService()
    return _service
