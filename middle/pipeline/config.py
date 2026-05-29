from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .channel_registry import (
    Site,
    ChannelAccount,
    migrate_accounts_from_themes,
    parse_channel_accounts,
    parse_sites,
)
from .themes import Theme, all_feed_kinds, parse_themes


def repo_root() -> Path:
    """VideoShortsAgent 仓库根（middle 的上级）。"""
    return Path(__file__).resolve().parents[2]


@dataclass
class PipelineConfig:
    soul_base_url: str = "https://ai-trends.news"
    soul_feed: str = "apps"
    soul_replication_high_value: bool = True
    soul_published_within_days: int = 3
    soul_page_size: int = 20
    min_worth_score: int = 7
    feed_kinds: list[str] = field(default_factory=lambda: ["apps"])
    data_dir: Path = field(default_factory=lambda: Path("./data"))
    vsa_root: Path | None = None
    broll_template: str = ""
    public_base_url: str = "https://ai-trends.news"
    render_enabled: bool = False
    render_mode: str = "pipeline"
    default_segments: str = "0:00-0:45"
    render_platforms: list[str] = field(default_factory=lambda: ["douyin", "xhs"])
    render_use_remotion: bool = False
    render_skip_tts: bool = False
    render_allow_template_fallback: bool = False
    llm_enabled: bool = True
    llm_api_key: str = ""
    llm_api_key_env: str = "DASHSCOPE_API_KEY"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen-plus"
    themes: list[Theme] = field(default_factory=lambda: parse_themes(None))
    sites: list[Site] = field(default_factory=list)
    channel_accounts: list[ChannelAccount] = field(default_factory=list)
    publisher: Any = field(default=None)
    config_path: Path | None = None

    def __post_init__(self) -> None:
        if self.publisher is None:
            from publisher.batches import parse_publisher_config

            self.publisher = parse_publisher_config(None)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "pipeline.db"

    @property
    def output_root(self) -> Path:
        return self.data_dir / "output"


def load_config(path: str | Path = "config.yaml") -> PipelineConfig:
    p = Path(path)
    raw: dict[str, Any] = {}
    if p.is_file():
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    soul = raw.get("soul") or {}
    filt = raw.get("filter") or {}
    paths = raw.get("paths") or {}
    site = raw.get("site") or {}
    render = raw.get("render") or {}
    llm = raw.get("llm") or {}
    themes_raw = raw.get("themes")
    sites_raw = raw.get("sites")
    accounts_raw = raw.get("channel_accounts")

    data_dir = Path(paths.get("data_dir") or "./data")
    vsa_raw = (paths.get("vsa_root") or "").strip()
    vsa_root = Path(vsa_raw) if vsa_raw else repo_root()

    themes = parse_themes(themes_raw if isinstance(themes_raw, list) else None)
    sites = parse_sites(sites_raw if isinstance(sites_raw, list) else None, themes)

    from publisher.batches import parse_publisher_config

    publisher = parse_publisher_config(raw.get("publisher"))
    channel_accounts = parse_channel_accounts(
        accounts_raw if isinstance(accounts_raw, list) else None,
        sites=sites,
        batches=publisher.batches,
    )
    # 仅当 yaml 未声明 channel_accounts 时从 themes 迁移；显式 [] 表示尚未配置卡片
    if accounts_raw is None and not channel_accounts:
        channel_accounts = migrate_accounts_from_themes(themes, sites)
    for acc in channel_accounts:
        if not acc.batch_id:
            b = publisher.batch_for_site(acc.site_code)
            if b:
                acc.batch_id = b.batch_id
    feed_kinds_cfg = filt.get("feed_kinds")
    if feed_kinds_cfg is not None:
        feed_kinds = list(feed_kinds_cfg)
    else:
        feed_kinds = all_feed_kinds(themes)

    return PipelineConfig(
        soul_base_url=str(soul.get("base_url") or "https://ai-trends.news").rstrip("/"),
        soul_feed=str(soul.get("feed") or "apps"),
        soul_replication_high_value=bool(soul.get("replication_high_value", True)),
        soul_published_within_days=int(soul.get("published_within_days") or 3),
        soul_page_size=int(soul.get("page_size") or 20),
        min_worth_score=int(filt.get("min_worth_score") or 7),
        feed_kinds=feed_kinds,
        data_dir=data_dir,
        vsa_root=vsa_root,
        broll_template=str(paths.get("broll_template") or render.get("broll_template") or ""),
        public_base_url=str(site.get("public_base_url") or "https://ai-trends.news").rstrip("/"),
        render_enabled=bool(render.get("enabled", False)),
        render_mode=str(render.get("mode") or "pipeline"),
        default_segments=str(render.get("default_segments") or "0:00-0:45"),
        render_platforms=list(render.get("platforms") or ["douyin", "xhs"]),
        render_use_remotion=bool(render.get("use_remotion", False)),
        render_skip_tts=bool(render.get("skip_tts", False)),
        render_allow_template_fallback=bool(render.get("allow_template_fallback", False)),
        llm_enabled=bool(llm.get("enabled", True)),
        llm_api_key=str(llm.get("api_key") or ""),
        llm_api_key_env=str(llm.get("api_key_env") or "DASHSCOPE_API_KEY"),
        llm_base_url=str(llm.get("base_url") or "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        llm_model=str(llm.get("model") or "qwen-plus"),
        themes=themes,
        sites=sites,
        channel_accounts=channel_accounts,
        publisher=publisher,
        config_path=p if p.is_file() else None,
    )
