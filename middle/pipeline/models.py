from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


def content_key_for_article(article_id: int) -> str:
    return f"aisoul:article:{article_id}"


def brief_hash(brief: dict[str, Any]) -> str:
    """口播结构哈希：仅核心字段参与，避免无关字段导致误重渲。"""
    core = {
        "hook": brief.get("hook"),
        "talking_points": brief.get("talking_points"),
        "cta": brief.get("cta"),
        "tags": brief.get("tags"),
    }
    blob = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


@dataclass
class VideoBrief:
    content_key: str
    article_id: int
    title: str
    hook: str
    talking_points: list[str]
    cta: str
    tags: list[str]
    worth_score: int | None = None
    feed_kind: str = "apps"
    source_key: str = ""
    theme_id: str = ""
    detail_url: str = ""
    source_url: str = ""
    cover_image_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def hash(self) -> str:
        return brief_hash(self.to_dict())


@dataclass
class RunStats:
    discovered: int = 0
    skipped: int = 0
    queued: int = 0
    rendered: int = 0
    packed: int = 0
    failed: int = 0
    deduped: int = 0
    errors: list[str] = field(default_factory=list)
