from __future__ import annotations

import json
import mimetypes
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pipeline.config import PipelineConfig, load_config
from pipeline.db import JobStore
from pipeline.models import RunStats, content_key_for_article
from pipeline.orchestrator import run_pipeline

from .state import record_run, release_run, run_status, try_acquire_run

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIST = ROOT / "frontend" / "dist"

_cfg: PipelineConfig | None = None


def get_cfg() -> PipelineConfig:
    global _cfg
    if _cfg is None:
        import os

        env_path = os.environ.get("PIPELINE_CONFIG", "").strip()
        if env_path:
            path = Path(env_path)
        else:
            path = ROOT / "config.yaml"
        _cfg = load_config(path if path.is_file() else ROOT / "config.example.yaml")
    return _cfg


def get_store() -> JobStore:
    cfg = get_cfg()
    return JobStore(cfg.db_path)


def _envelope(data: Any) -> dict[str, Any]:
    return {"code": 0, "message": "ok", "data": data}


def _parse_job(job: dict[str, Any]) -> dict[str, Any]:
    out = dict(job)
    for key in ("soul_snapshot", "brief_json"):
        raw = out.get(key)
        if isinstance(raw, str) and raw:
            try:
                out[key] = json.loads(raw)
            except json.JSONDecodeError:
                pass
    return out


def _safe_output_path(article_id: int, rel: str) -> Path:
    cfg = get_cfg()
    base = (cfg.output_root / str(article_id)).resolve()
    target = (base / rel).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(400, "invalid path")
    if not target.is_file():
        raise HTTPException(404, "file not found")
    return target


app = FastAPI(title="AiSoul Pipeline", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PublishBody(BaseModel):
    article_id: int
    channel: str = Field(..., pattern="^(douyin|xhs|toutiao|douban)$")
    note: str = ""


@app.get("/api/v1/capabilities")
def vsa_capabilities():
    """VSA 特效/样式/转场能力目录（供连接器与 LLM 对齐）。"""
    import sys

    root = ROOT.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from python_agent.capabilities.registry import effects_catalog, llm_capabilities_section, PLATFORM_VIDEO_DEFAULTS

    return _envelope(
        {
            "catalog": effects_catalog(),
            "platform_defaults": PLATFORM_VIDEO_DEFAULTS,
            "prompt_section": llm_capabilities_section(),
        }
    )


@app.get("/api/v1/health")
def health():
    cfg = get_cfg()
    return _envelope(
        {
            "service": "aisoul-pipeline",
            "soul_base_url": cfg.soul_base_url,
            "data_dir": str(cfg.data_dir),
        }
    )


@app.get("/api/v1/publishing/stats")
def publishing_stats_api(days: int = Query(30, ge=1, le=90)):
    from pipeline.publish_stats import publishing_overview

    return _envelope(publishing_overview(get_cfg(), get_store(), days=days))


@app.get("/api/v1/dashboard")
def dashboard():
    store = get_store()
    jobs = store.list_jobs()
    by_status: dict[str, int] = {}
    for j in jobs:
        st = j.get("status") or "unknown"
        by_status[st] = by_status.get(st, 0) + 1
    pending = {
        ch: len(store.pending_publish(ch)) for ch in ("douyin", "xhs", "toutiao", "douban")
    }
    return _envelope(
        {
            "job_counts": by_status,
            "total_jobs": len(jobs),
            "pending_publish": pending,
            "run": run_status(),
        }
    )


@app.get("/api/v1/jobs")
def list_jobs(status: str | None = Query(None)):
    store = get_store()
    if status:
        rows = store.list_jobs(tuple(s.strip() for s in status.split(",") if s.strip()))
    else:
        rows = store.list_jobs()
    return _envelope([_parse_job(j) for j in rows])


@app.get("/api/v1/jobs/{article_id}")
def get_job(article_id: int):
    store = get_store()
    ck = content_key_for_article(article_id)
    job = store.get_job(ck)
    if not job:
        raise HTTPException(404, "job not found")
    cfg = get_cfg()
    out_dir = cfg.output_root / str(article_id)
    artifacts: list[dict[str, str]] = []
    if out_dir.is_dir():
        for p in sorted(out_dir.rglob("*")):
            if p.is_file():
                rel = p.relative_to(out_dir).as_posix()
                artifacts.append({"path": rel, "url": f"/api/v1/files/{article_id}/{rel}"})
    data = _parse_job(job)
    data["artifacts"] = artifacts
    data["events"] = store.list_events(ck)
    channels = ["douyin", "xhs", "toutiao", "douban"]
    data["published"] = {ch: store.is_published(ck, ch) for ch in channels}
    return _envelope(data)


@app.get("/api/v1/pending/{channel}")
def pending(channel: str):
    if channel not in ("douyin", "xhs", "toutiao", "douban"):
        raise HTTPException(400, "invalid channel")
    store = get_store()
    return _envelope([_parse_job(j) for j in store.pending_publish(channel)])


@app.post("/api/v1/publish")
def mark_publish(body: PublishBody):
    store = get_store()
    ck = content_key_for_article(body.article_id)
    if not store.get_job(ck):
        raise HTTPException(404, "job not found")
    job = store.get_job(ck)
    if job and job.get("status") not in ("ready_to_publish", "completed", "packed", "rendered", "processing"):
        raise HTTPException(400, f"任务状态 {job.get('status')} 不可标记发布")
    created = store.mark_published(ck, body.channel, body.note)
    return _envelope({"created": created, "content_key": ck, "channel": body.channel})


@app.post("/api/v1/run")
def trigger_run():
    if not try_acquire_run():
        raise HTTPException(409, "pipeline already running")

    def _work() -> None:
        try:
            stats = run_pipeline(get_cfg())
            record_run(stats)
        except Exception as e:
            record_run(RunStats(), error=f"{type(e).__name__}: {e}")
        finally:
            release_run()

    threading.Thread(target=_work, daemon=True).start()
    return _envelope({"started": True})


@app.get("/api/v1/run/status")
def get_run_status():
    return _envelope(run_status())


@app.get("/api/v1/files/{article_id}/{file_path:path}")
def get_file(article_id: int, file_path: str):
    path = _safe_output_path(article_id, file_path)
    media = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media)


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
