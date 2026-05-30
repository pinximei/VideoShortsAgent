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
_cfg_lock = threading.Lock()


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


def reload_cfg() -> PipelineConfig:
    global _cfg
    with _cfg_lock:
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
    account_id: str = ""


class ThemePatchBody(BaseModel):
    theme_id: str = Field(..., min_length=1, max_length=64)


class ChannelAccountBody(BaseModel):
    id: str = ""
    site_code: str = Field(..., min_length=1, max_length=64)
    channel_id: str = Field(..., pattern="^(douyin|xhs|toutiao|douban)$")
    label: str = ""
    handle: str = ""
    profile_url: str = ""
    login_hint: str = ""
    note: str = ""
    enabled: bool = True
    is_primary: bool = False
    batch_id: str = ""


class ChannelAccountCardBody(BaseModel):
    id: str = ""
    label: str = ""
    handle: str = ""
    profile_url: str = ""
    login_hint: str = ""
    note: str = ""
    enabled: bool = True
    is_primary: bool = False
    batch_id: str = ""


class ChannelAccountsBatchBody(BaseModel):
    site_code: str = Field(..., min_length=1, max_length=64)
    channel_id: str = Field(..., pattern="^(douyin|xhs|toutiao|douban)$")
    accounts: list[ChannelAccountCardBody] = Field(default_factory=list)


class LlmSettingsBody(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    enabled: bool | None = None


@app.get("/api/v1/settings/llm")
def get_llm_settings_api():
    from pipeline.llm_settings import llm_settings_public

    return _envelope(llm_settings_public(get_cfg()))


@app.put("/api/v1/settings/llm")
def put_llm_settings_api(body: LlmSettingsBody):
    from pipeline.llm_settings import llm_settings_public, save_llm_settings

    cfg_path = ROOT / "config.yaml"
    if not cfg_path.is_file():
        cfg_path = ROOT / "config.example.yaml"
    save_llm_settings(
        api_key=body.api_key or None,
        base_url=body.base_url or None,
        model=body.model or None,
        enabled=body.enabled,
        config_yaml=cfg_path if cfg_path.is_file() else None,
    )
    reload_cfg()
    return _envelope(llm_settings_public(get_cfg()))


@app.post("/api/v1/settings/llm/test")
def test_llm_settings_api():
    from pipeline.llm_settings import test_llm_connection

    cfg = reload_cfg()
    try:
        result = test_llm_connection(cfg)
        return _envelope(result)
    except Exception as e:
        raise HTTPException(400, f"LLM 测试失败: {type(e).__name__}: {str(e)[:300]}")


@app.get("/api/v1/channel-config")
def channel_config_overview_api():
    from pipeline.channel_config import get_overview

    return _envelope(get_overview(get_cfg()))


@app.get("/api/v1/channel-config/accounts")
def channel_config_accounts(site_code: str = Query(...), channel_id: str = Query(...)):
    from pipeline.channel_registry import accounts_for

    cfg = get_cfg()
    if not any(s.code == site_code for s in cfg.sites):
        raise HTTPException(400, "unknown site_code")
    rows = accounts_for(cfg.channel_accounts, site_code=site_code, channel_id=channel_id)
    return _envelope([a.to_dict() for a in rows])


@app.put("/api/v1/channel-config/accounts")
def channel_config_save_accounts(body: ChannelAccountsBatchBody):
    from pipeline.channel_config import replace_accounts_for_slot

    try:
        cfg = replace_accounts_for_slot(
            get_cfg(),
            site_code=body.site_code,
            channel_id=body.channel_id,
            cards=[c.model_dump() for c in body.accounts],
        )
        global _cfg
        _cfg = cfg
        from pipeline.channel_registry import accounts_for

        rows = accounts_for(cfg.channel_accounts, site_code=body.site_code, channel_id=body.channel_id)
        return _envelope({"saved": len(rows), "accounts": [a.to_dict() for a in rows]})
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/v1/channel-config/accounts")
def channel_config_upsert_account(body: ChannelAccountBody):
    from pipeline.channel_config import upsert_account

    try:
        cfg, acc = upsert_account(get_cfg(), body.model_dump())
        global _cfg
        _cfg = cfg
        return _envelope(acc.to_dict())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.delete("/api/v1/channel-config/accounts/{account_id}")
def channel_config_delete_account(account_id: str):
    from pipeline.channel_config import delete_account

    cfg = delete_account(get_cfg(), account_id)
    global _cfg
    _cfg = cfg
    return _envelope({"deleted": account_id})


class PublisherPublishBody(BaseModel):
    article_id: int
    channel_id: str = Field(..., pattern="^(douyin|xhs|toutiao|douban)$")
    account_id: str = ""
    dry_run: bool = False


class PublisherLoginCheckBody(BaseModel):
    account_id: str = Field(..., min_length=1, max_length=64)


@app.get("/api/v1/publisher/overview")
def publisher_overview_api():
    from publisher.runner import publisher_overview

    return _envelope(publisher_overview(get_cfg()))


@app.post("/api/v1/publisher/publish")
def publisher_publish_api(body: PublisherPublishBody):
    from publisher.runner import PublishRequest, publish_content

    try:
        result = publish_content(
            get_cfg(),
            PublishRequest(
                article_id=body.article_id,
                channel_id=body.channel_id,
                account_id=body.account_id or None,
                dry_run=body.dry_run,
            ),
        )
        return _envelope(result.__dict__)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e


@app.post("/api/v1/publisher/login-check")
def publisher_login_check_api(body: PublisherLoginCheckBody):
    from publisher.runner import check_login

    cfg = get_cfg()
    acc = next((a for a in cfg.channel_accounts if a.id == body.account_id), None)
    if not acc:
        raise HTTPException(404, "account not found")
    batch = cfg.publisher.batch_for_site(acc.site_code) if acc.site_code else None
    batch_id = acc.batch_id or (batch.batch_id if batch else "")
    if not batch_id:
        raise HTTPException(400, "account has no batch_id")
    try:
        return _envelope(check_login(cfg, batch_id, acc))
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e


@app.get("/api/v1/themes")
def list_themes():
    cfg = get_cfg()
    return _envelope([t.to_dict() for t in cfg.themes])


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
    from pipeline.llm_settings import llm_settings_public

    cfg = get_cfg()
    llm = llm_settings_public(cfg)
    return _envelope(
        {
            "service": "aisoul-pipeline",
            "soul_base_url": cfg.soul_base_url,
            "data_dir": str(cfg.data_dir),
            "llm_configured": llm.get("api_key_set"),
            "llm_model": llm.get("model"),
        }
    )


@app.get("/api/v1/publishing/stats")
def publishing_stats_api(days: int = Query(30, ge=1, le=90), theme: str | None = Query(None)):
    from pipeline.publish_stats import publishing_overview

    return _envelope(publishing_overview(get_cfg(), get_store(), days=days, theme_id=theme or None))


@app.get("/api/v1/dashboard")
def dashboard(theme: str | None = Query(None)):
    store = get_store()
    cfg = get_cfg()
    jobs = store.list_jobs(theme_id=theme or None)
    by_status: dict[str, int] = {}
    for j in jobs:
        st = j.get("status") or "unknown"
        by_status[st] = by_status.get(st, 0) + 1
    theme_ids = [t.id for t in cfg.themes]
    pending_matrix = store.count_pending_by_theme_channel(theme_ids, ("douyin", "xhs", "toutiao", "douban"))
    pending = {
        ch: len(store.pending_publish(ch, theme_id=theme or None))
        for ch in ("douyin", "xhs", "toutiao", "douban")
    }
    return _envelope(
        {
            "themes": [t.to_dict() for t in cfg.themes],
            "theme_id": theme,
            "job_counts": by_status,
            "total_jobs": len(jobs),
            "pending_publish": pending,
            "pending_by_theme_channel": pending_matrix,
            "run": run_status(),
        }
    )


@app.get("/api/v1/jobs")
def list_jobs(status: str | None = Query(None), theme: str | None = Query(None)):
    store = get_store()
    if status:
        rows = store.list_jobs(
            tuple(s.strip() for s in status.split(",") if s.strip()),
            theme_id=theme or None,
        )
    else:
        rows = store.list_jobs(theme_id=theme or None)
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
    from pipeline.channel_registry import accounts_for, primary_account_label, site_for_theme
    from pipeline.publish_guard import bindings_from_job

    data = _parse_job(job)
    data["artifacts"] = artifacts
    data["events"] = store.list_events(ck)
    tid = job.get("theme_id") or ""
    theme_obj = next((t.to_dict() for t in cfg.themes if t.id == tid), None)
    data["theme"] = theme_obj
    site = site_for_theme(cfg.sites, tid)
    data["site"] = site.to_dict() if site else None
    channels = ["douyin", "xhs", "toutiao", "douban"]
    data["published"] = {ch: store.is_published(ck, ch) for ch in channels}
    bindings = bindings_from_job(job)
    data["publish_bindings"] = bindings
    if bindings:
        data["account_labels"] = {
            ch: (bindings.get("channels") or {}).get(ch, {}).get("label") or ch
            for ch in channels
        }
    else:
        data["account_labels"] = {
            ch: primary_account_label(
                cfg.channel_accounts,
                cfg.sites,
                theme_id=tid,
                channel_id=ch,
                fallback=(theme_obj or {}).get("accounts", {}).get(ch, {}).get("label") or ch,
            )
            for ch in channels
        }
    if site:
        data["channel_accounts"] = {
            ch: [a.to_dict() for a in accounts_for(cfg.channel_accounts, site_code=site.code, channel_id=ch)]
            for ch in channels
        }
    return _envelope(data)


@app.get("/api/v1/pending/{channel}")
def pending(channel: str, theme: str | None = Query(None)):
    if channel not in ("douyin", "xhs", "toutiao", "douban"):
        raise HTTPException(400, "invalid channel")
    store = get_store()
    return _envelope([_parse_job(j) for j in store.pending_publish(channel, theme_id=theme or None)])


@app.post("/api/v1/publish")
def mark_publish(body: PublishBody):
    store = get_store()
    ck = content_key_for_article(body.article_id)
    if not store.get_job(ck):
        raise HTTPException(404, "job not found")
    job = store.get_job(ck)
    if job and job.get("status") not in ("ready_to_publish", "completed", "packed", "rendered", "processing"):
        raise HTTPException(400, f"任务状态 {job.get('status')} 不可标记发布")

    from pipeline.publish_guard import PublishGuardError, validate_publish_target

    cfg = get_cfg()
    try:
        ch_bind, acc, _bindings = validate_publish_target(
            cfg, job, body.channel, body.account_id or None
        )
        account_id = acc.id
    except PublishGuardError as e:
        raise HTTPException(409, detail={"code": e.code, "message": e.message}) from e

    created = store.mark_published(ck, body.channel, body.note, account_id)
    if created:
        store.log_event(
            ck,
            status=job.get("status") or "ready_to_publish",
            step="publish_mark",
            message=f"已标记发布: {body.channel} @ {ch_bind.get('label')} ({account_id})",
        )
    return _envelope(
        {
            "created": created,
            "content_key": ck,
            "channel": body.channel,
            "account_id": account_id,
            "account_label": ch_bind.get("label"),
        }
    )


@app.patch("/api/v1/jobs/{article_id}/theme")
def patch_job_theme(article_id: int, body: ThemePatchBody):
    cfg = get_cfg()
    if not any(t.id == body.theme_id for t in cfg.themes):
        raise HTTPException(400, "unknown theme_id")
    store = get_store()
    ck = content_key_for_article(article_id)
    job = store.get_job(ck)
    if not job:
        raise HTTPException(404, "job not found")
    if store.published_channels(ck):
        raise HTTPException(400, "已标记发布，不可更改赛道（防止发串号）")

    from pipeline.publish_guard import refresh_job_bindings

    raw_brief = job.get("brief_json")
    brief: dict = {}
    if isinstance(raw_brief, str) and raw_brief:
        import json

        try:
            brief = json.loads(raw_brief)
        except json.JSONDecodeError:
            brief = {}
    elif isinstance(raw_brief, dict):
        brief = dict(raw_brief)

    new_brief = refresh_job_bindings(cfg, body.theme_id, brief)
    store.update_job(ck, theme_id=body.theme_id, brief_json=new_brief)
    store.log_event(ck, status=job.get("status") or "", step="theme", message=f"赛道改为 {body.theme_id}，已重建发布绑定")
    return _envelope({"content_key": ck, "theme_id": body.theme_id, "publish_bindings": new_brief.get("publish_bindings")})


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
