"""发布执行器：路由 batch → slot → profile → 固定脚本。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pipeline.channel_registry import ChannelAccount, accounts_for, site_for_theme
from pipeline.config import PipelineConfig
from pipeline.models import content_key_for_article

from .browser_pool import get_pool
from .profiles import read_session_meta, write_session_meta
from .scripts.base import PublishPack
from .scripts.registry import get_login_script, get_publish_script


def _account_in_batch(account: ChannelAccount, batch, batch_id: str, sites) -> bool:
    if account.batch_id and account.batch_id != batch_id:
        return False
    if batch:
        site = site_for_theme(sites, batch.theme_id)
        if site and account.site_code != site.code:
            return False
    return True


@dataclass
class PublishRequest:
    article_id: int
    channel_id: str
    account_id: str | None = None
    dry_run: bool = False


@dataclass
class PublishResult:
    ok: bool
    batch_id: str
    slot_id: int
    account_id: str
    channel_id: str
    script: str
    steps: list[dict]
    message: str = ""


def _resolve_account(cfg: PipelineConfig, req: PublishRequest) -> tuple[str, ChannelAccount]:
    job_theme = ""
    from pipeline.db import JobStore

    store = JobStore(cfg.db_path)
    job = store.get_job(content_key_for_article(req.article_id))
    if job:
        job_theme = job.get("theme_id") or ""

    batch = cfg.publisher.batch_for_theme(job_theme) if job_theme else None
    if not batch:
        raise ValueError(f"no publisher batch for theme={job_theme or '?'}")

    site = site_for_theme(cfg.sites, batch.theme_id)
    if not site:
        raise ValueError(f"no site for theme={batch.theme_id}")

    if req.account_id:
        acc = next((a for a in cfg.channel_accounts if a.id == req.account_id), None)
        if not acc:
            raise ValueError(f"unknown account_id={req.account_id}")
    else:
        rows = accounts_for(
            cfg.channel_accounts,
            site_code=site.code,
            channel_id=req.channel_id,
            enabled_only=True,
        )
        if not rows:
            raise ValueError(f"no account for {site.code}/{req.channel_id}")
        acc = rows[0]

    if acc.batch_id and acc.batch_id != batch.batch_id:
        raise ValueError(f"account {acc.id} batch mismatch")

    return batch.batch_id, acc


def _load_publish_pack(cfg: PipelineConfig, article_id: int, channel_id: str) -> PublishPack:
    out_dir = cfg.output_root / str(article_id)
    title_path = out_dir / "publish" / f"{channel_id}_title.txt"
    video_candidates = list(out_dir.glob(f"video_{channel_id}*.mp4")) + list(out_dir.glob("*.mp4"))
    video_path = video_candidates[0] if video_candidates else None
    title = title_path.read_text(encoding="utf-8").strip() if title_path.is_file() else ""
    return PublishPack(
        article_id=article_id,
        channel_id=channel_id,
        title=title,
        video_path=video_path,
        output_dir=out_dir,
    )


def check_login(cfg: PipelineConfig, batch_id: str, account: ChannelAccount) -> dict:
    slot = cfg.publisher.slot_for_batch(batch_id)
    if not slot:
        raise ValueError(f"no slot for batch={batch_id}")

    pool = get_pool(cfg.publisher)
    runner = pool.runner_for_batch(batch_id)
    script = get_login_script(account.channel_id)

    def _work(page):
        return script.check(page)

    result = runner.run_with_account(cfg.data_dir, account, _work)
    status = "ok" if result.get("logged_in") else "expired"
    write_session_meta(
        cfg.data_dir,
        batch_id,
        account.id,
        status=status,
        message="login check",
    )
    return {
        "batch_id": batch_id,
        "slot_id": slot.slot_id,
        "account_id": account.id,
        **result,
    }


def publish_content(cfg: PipelineConfig, req: PublishRequest) -> PublishResult:
    batch_id, account = _resolve_account(cfg, req)
    slot = cfg.publisher.slot_for_batch(batch_id)
    if not slot:
        raise ValueError(f"no slot for batch={batch_id}")

    pack = _load_publish_pack(cfg, req.article_id, req.channel_id)
    if req.dry_run:
        script = get_publish_script(req.channel_id)
        return PublishResult(
            ok=True,
            batch_id=batch_id,
            slot_id=slot.slot_id,
            account_id=account.id,
            channel_id=req.channel_id,
            script=script.__class__.__name__,
            steps=[{"step": s, "ok": True, "detail": "dry_run"} for s in script.fixed_steps],
            message="dry_run",
        )

    pool = get_pool(cfg.publisher)
    runner = pool.runner_for_batch(batch_id)
    script = get_publish_script(req.channel_id)

    def _work(page):
        return script.run(page, pack)

    raw = runner.run_with_account(cfg.data_dir, account, _work)
    if raw.get("ok"):
        write_session_meta(cfg.data_dir, batch_id, account.id, status="ok", message="publish ok")
    return PublishResult(
        ok=bool(raw.get("ok")),
        batch_id=batch_id,
        slot_id=slot.slot_id,
        account_id=account.id,
        channel_id=req.channel_id,
        script=str(raw.get("script") or ""),
        steps=list(raw.get("steps") or []),
        message="",
    )


def publisher_overview(cfg: PipelineConfig) -> dict:
    slots_out = []
    for slot in cfg.publisher.slots:
        batch = cfg.publisher.batch_by_id(slot.batch_id)
        accounts = [a for a in cfg.channel_accounts if _account_in_batch(a, batch, slot.batch_id, cfg.sites)]
        acc_meta = []
        for a in accounts:
            meta = read_session_meta(cfg.data_dir, slot.batch_id, a.id)
            acc_meta.append({**a.to_dict(), "session": meta})
        slots_out.append(
            {
                **slot.to_dict(),
                "batch": batch.to_dict() if batch else None,
                "accounts": acc_meta,
            }
        )

    pool = get_pool(cfg.publisher)
    return {
        "publisher": cfg.publisher.to_dict(),
        "slots": slots_out,
        "browser_pool": pool.status(),
        "note": "网页操作全部由固定 Playwright 脚本执行，不使用大模型点击。",
    }
