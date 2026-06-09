"""发布后验收执行器（复用浏览器池 + Profile）。"""
from __future__ import annotations

from dataclasses import dataclass

from pipeline.config import PipelineConfig

from ..browser_pool import get_pool
from ..runner import PublishRequest, _resolve_account
from .pack import load_verify_pack
from .scripts.registry import get_verify_script


@dataclass
class VerifyRequest:
    article_id: int
    channel_id: str
    account_id: str | None = None


@dataclass
class VerifyResult:
    ok: bool
    verified: bool
    batch_id: str
    slot_id: int
    account_id: str
    channel_id: str
    script: str
    steps: list[dict]
    evidence: dict
    title_needle: str = ""


def verify_published(cfg: PipelineConfig, req: VerifyRequest) -> VerifyResult:
    pub_req = PublishRequest(
        article_id=req.article_id,
        channel_id=req.channel_id,
        account_id=req.account_id,
    )
    batch_id, account = _resolve_account(cfg, pub_req)
    slot = cfg.publisher.slot_for_batch(batch_id)
    if not slot:
        raise ValueError(f"no slot for batch={batch_id}")

    pack = load_verify_pack(cfg, req.article_id, req.channel_id)
    pool = get_pool(cfg.publisher)
    runner = pool.runner_for_batch(batch_id)
    script = get_verify_script(req.channel_id)

    def _work(page):
        return script.run(page, pack)

    raw = runner.run_with_account(cfg.data_dir, account, _work)
    return VerifyResult(
        ok=bool(raw.get("ok")),
        verified=bool(raw.get("verified")),
        batch_id=batch_id,
        slot_id=slot.slot_id,
        account_id=account.id,
        channel_id=req.channel_id,
        script=str(raw.get("script") or ""),
        steps=list(raw.get("steps") or []),
        evidence=dict(raw.get("evidence") or {}),
        title_needle=str(raw.get("title_needle") or pack.title_needle),
    )
