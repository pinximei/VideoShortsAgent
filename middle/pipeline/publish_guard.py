"""任务就绪时冻结「文章 → 账号」绑定，发布时强校验，防止发串号。"""
from __future__ import annotations

import json
from typing import Any

from .channel_registry import ChannelAccount, accounts_for, site_for_theme
from .config import PipelineConfig
from .job_flow import PUBLISH_CHANNELS


class PublishGuardError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def build_publish_bindings(cfg: PipelineConfig, theme_id: str) -> dict[str, Any]:
    """根据赛道生成各渠道唯一绑定账号（打包时写入 brief，后续不可随意串号）。"""
    if not theme_id:
        raise PublishGuardError("missing_theme", "无赛道，无法生成发布绑定")

    batch = cfg.publisher.batch_for_theme(theme_id)
    if not batch:
        raise PublishGuardError("missing_batch", f"赛道 {theme_id} 未配置发布批次")

    site = site_for_theme(cfg.sites, batch.theme_id)
    site_code = site.code if site else (batch.site_code or "")
    site_label = site.label if site else batch.label
    if not site_code:
        raise PublishGuardError("missing_site", f"赛道 {theme_id} 未绑定站点")

    channels: dict[str, dict[str, Any]] = {}
    for ch in PUBLISH_CHANNELS:
        rows = accounts_for(
            cfg.channel_accounts,
            site_code=site_code,
            channel_id=ch,
            enabled_only=True,
        )
        if not rows:
            continue
        acc = next((a for a in rows if a.is_primary), rows[0])
        channels[ch] = {
            "account_id": acc.id,
            "label": acc.label or acc.handle or acc.id,
            "batch_id": batch.batch_id,
            "site_code": site_code,
            "channel_id": ch,
        }

    return {
        "theme_id": theme_id,
        "batch_id": batch.batch_id,
        "batch_label": batch.label,
        "site_code": site_code,
        "site_label": site_label,
        "channels": channels,
    }


def bindings_from_job(job: dict[str, Any]) -> dict[str, Any] | None:
    raw = job.get("brief_json")
    if isinstance(raw, str) and raw:
        try:
            brief = json.loads(raw)
        except json.JSONDecodeError:
            return None
    elif isinstance(raw, dict):
        brief = raw
    else:
        return None
    bindings = brief.get("publish_bindings")
    return bindings if isinstance(bindings, dict) else None


def validate_publish_target(
    cfg: PipelineConfig,
    job: dict[str, Any],
    channel_id: str,
    account_id: str | None = None,
) -> tuple[dict[str, Any], ChannelAccount, dict[str, Any]]:
    """
    校验发布目标。返回 (channel_binding, account, full_bindings)。
    账号与任务赛道/批次/站点不一致时抛出 PublishGuardError。
    """
    theme_id = str(job.get("theme_id") or "").strip()
    if not theme_id:
        raise PublishGuardError("job_missing_theme", "任务未绑定赛道，禁止发布")

    bindings = bindings_from_job(job)
    if not bindings:
        bindings = build_publish_bindings(cfg, theme_id)

    if bindings.get("theme_id") != theme_id:
        raise PublishGuardError(
            "theme_binding_mismatch",
            f"任务赛道 {theme_id} 与冻结绑定 {bindings.get('theme_id')} 不一致，禁止发布",
        )

    ch_bind = (bindings.get("channels") or {}).get(channel_id)
    if not ch_bind:
        raise PublishGuardError(
            "no_binding_for_channel",
            f"渠道 {channel_id} 在此赛道下无绑定账号，禁止发布",
        )

    expected_id = str(ch_bind.get("account_id") or "")
    use_id = (account_id or expected_id).strip()
    if not use_id:
        raise PublishGuardError("missing_account_id", "未指定发布账号")

    if use_id != expected_id:
        expected_label = ch_bind.get("label") or expected_id
        raise PublishGuardError(
            "account_mismatch",
            f"禁止发串号：本篇只能由账号「{expected_label}」({expected_id}) 发布，"
            f"不能使用 {account_id}",
        )

    acc = next((a for a in cfg.channel_accounts if a.id == use_id), None)
    if not acc:
        raise PublishGuardError("unknown_account", f"账号 {use_id} 不存在")

    if acc.channel_id != channel_id:
        raise PublishGuardError(
            "channel_mismatch",
            f"账号 {use_id} 属于渠道 {acc.channel_id}，不能用于 {channel_id}",
        )

    if acc.site_code != bindings.get("site_code"):
        raise PublishGuardError(
            "site_mismatch",
            f"账号站点 {acc.site_code} 与文章站点 {bindings.get('site_code')} 不一致",
        )

    acc_batch = acc.batch_id or bindings.get("batch_id")
    if acc_batch and bindings.get("batch_id") and acc_batch != bindings.get("batch_id"):
        raise PublishGuardError(
            "batch_mismatch",
            f"账号批次 {acc_batch} 与文章批次 {bindings.get('batch_id')} 不一致",
        )

    if not acc.enabled:
        raise PublishGuardError("account_disabled", f"账号 {use_id} 已禁用")

    return ch_bind, acc, bindings


def refresh_job_bindings(cfg: PipelineConfig, theme_id: str, brief_json: dict[str, Any]) -> dict[str, Any]:
    """赛道变更后重建绑定（会覆盖旧绑定）。"""
    out = dict(brief_json)
    out["publish_bindings"] = build_publish_bindings(cfg, theme_id)
    out["theme_id"] = theme_id
    return out
