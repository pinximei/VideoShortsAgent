"""渠道账号配置持久化。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .channel_registry import (
    ChannelAccount,
    Site,
    accounts_for,
    channel_config_overview,
    migrate_accounts_from_themes,
    new_account_id,
    normalize_primary_flags,
    parse_channel_accounts,
    parse_sites,
    site_by_code,
    validate_account_payload,
)
from .config import PipelineConfig, load_config
from .config_store import read_yaml_dict, update_config_sections
from .themes import PUBLISH_CHANNEL_IDS, parse_themes


def config_file_path(cfg: PipelineConfig) -> Path:
    if cfg.config_path and cfg.config_path.is_file():
        return cfg.config_path
    return Path(__file__).resolve().parents[1] / "config.example.yaml"


def reload_config(cfg_path: Path) -> PipelineConfig:
    return load_config(cfg_path)


def save_channel_accounts(cfg: PipelineConfig, accounts: list[ChannelAccount]) -> None:
    path = config_file_path(cfg)
    payload = [a.to_dict() for a in accounts]
    update_config_sections(path, channel_accounts=payload)


def save_sites(cfg: PipelineConfig, sites: list[Site]) -> None:
    path = config_file_path(cfg)
    update_config_sections(path, sites=[s.to_dict() for s in sites])


def upsert_account(cfg: PipelineConfig, data: dict[str, Any]) -> tuple[PipelineConfig, ChannelAccount]:
    accounts = list(cfg.channel_accounts)
    acc = validate_account_payload(data, cfg.sites)
    idx = next((i for i, a in enumerate(accounts) if a.id == acc.id), None)
    if idx is None:
        accounts.append(acc)
    else:
        accounts[idx] = acc
    if acc.is_primary:
        for a in accounts:
            if (
                a.id != acc.id
                and a.site_code == acc.site_code
                and a.channel_id == acc.channel_id
            ):
                a.is_primary = False
    normalize_primary_flags(accounts, site_code=acc.site_code, channel_id=acc.channel_id)
    save_channel_accounts(cfg, accounts)
    sync_theme_accounts_from_registry(cfg, accounts)
    path = config_file_path(cfg)
    return reload_config(path), acc


def delete_account(cfg: PipelineConfig, account_id: str) -> PipelineConfig:
    accounts = [a for a in cfg.channel_accounts if a.id != account_id]
    save_channel_accounts(cfg, accounts)
    sync_theme_accounts_from_registry(cfg, accounts)
    return reload_config(config_file_path(cfg))


def replace_accounts_for_slot(
    cfg: PipelineConfig,
    *,
    site_code: str,
    channel_id: str,
    cards: list[dict[str, Any]],
) -> PipelineConfig:
    if not site_by_code(cfg.sites, site_code):
        raise ValueError(f"unknown site_code: {site_code}")
    kept = [a for a in cfg.channel_accounts if not (a.site_code == site_code and a.channel_id == channel_id)]
    new_rows: list[ChannelAccount] = []
    for i, raw in enumerate(cards):
        raw = dict(raw)
        raw["site_code"] = site_code
        raw["channel_id"] = channel_id
        if not raw.get("id"):
            raw["id"] = new_account_id()
        if i == 0 and "is_primary" not in raw:
            raw["is_primary"] = True
        new_rows.append(validate_account_payload(raw, cfg.sites))
    normalize_primary_flags(new_rows, site_code=site_code, channel_id=channel_id)
    accounts = kept + new_rows
    save_channel_accounts(cfg, accounts)
    sync_theme_accounts_from_registry(cfg, accounts)
    return reload_config(config_file_path(cfg))


def sync_theme_accounts_from_registry(cfg: PipelineConfig, accounts: list[ChannelAccount] | None = None) -> None:
    """将各站点主账号同步回 themes.accounts，兼容旧逻辑与 LLM。"""
    path = config_file_path(cfg)
    raw = read_yaml_dict(path)
    themes_raw = raw.get("themes")
    themes = parse_themes(themes_raw if isinstance(themes_raw, list) else None)
    sites = parse_sites(raw.get("sites") if isinstance(raw.get("sites"), list) else None, themes)
    accs = accounts if accounts is not None else parse_channel_accounts(raw.get("channel_accounts"))
    theme_by_id = {t.id: t for t in themes}
    for site in sites:
        theme = theme_by_id.get(site.theme_id)
        if not theme:
            continue
        for ch_id in PUBLISH_CHANNEL_IDS:
            if ch_id not in theme.accounts:
                continue
            theme.accounts[ch_id].label = ""
            theme.accounts[ch_id].handle = ""
            theme.accounts[ch_id].note = ""
        for ch_id in PUBLISH_CHANNEL_IDS:
            if ch_id not in theme.accounts:
                continue
            rows = accounts_for(accs, site_code=site.code, channel_id=ch_id, enabled_only=True)
            if not rows:
                continue
            primary = next((a for a in rows if a.is_primary), rows[0])
            theme.accounts[ch_id].label = primary.label
            theme.accounts[ch_id].handle = primary.handle
            theme.accounts[ch_id].note = primary.note
    themes_payload = [t.to_dict() for t in themes]
    update_config_sections(path, themes=themes_payload)


def get_overview(cfg: PipelineConfig) -> dict[str, Any]:
    return channel_config_overview(cfg.sites, cfg.channel_accounts)
