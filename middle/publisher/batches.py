"""双批次 / 双浏览器槽位：一个 slot 固定服务一个 batch_id（主体）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_PUBLISHER: dict[str, Any] = {
    "headless": True,
    "slots": [
        {"slot_id": 1, "batch_id": "batch_a", "label": "主体A · AI变现"},
        {"slot_id": 2, "batch_id": "batch_b", "label": "主体B · AI资讯"},
    ],
    "batches": [
        {
            "batch_id": "batch_a",
            "site_code": "ai-trends-apps",
            "theme_id": "ai_monetize",
            "label": "AI 变现主体",
        },
        {
            "batch_id": "batch_b",
            "site_code": "ai-trends-news",
            "theme_id": "ai_news",
            "label": "AI 资讯主体",
        },
    ],
}


@dataclass
class PublisherSlot:
    slot_id: int
    batch_id: str
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"slot_id": self.slot_id, "batch_id": self.batch_id, "label": self.label}


@dataclass
class PublisherBatch:
    batch_id: str
    site_code: str
    theme_id: str
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "site_code": self.site_code,
            "theme_id": self.theme_id,
            "label": self.label,
        }


@dataclass
class PublisherConfig:
    headless: bool = True
    slots: list[PublisherSlot] = None  # type: ignore[assignment]
    batches: list[PublisherBatch] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.slots is None:
            self.slots = []
        if self.batches is None:
            self.batches = []

    def slot_for_batch(self, batch_id: str) -> PublisherSlot | None:
        for s in self.slots:
            if s.batch_id == batch_id:
                return s
        return None

    def batch_by_id(self, batch_id: str) -> PublisherBatch | None:
        for b in self.batches:
            if b.batch_id == batch_id:
                return b
        return None

    def batch_for_theme(self, theme_id: str) -> PublisherBatch | None:
        for b in self.batches:
            if b.theme_id == theme_id:
                return b
        return None

    def batch_for_site(self, site_code: str) -> PublisherBatch | None:
        for b in self.batches:
            if b.site_code == site_code:
                return b
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "headless": self.headless,
            "slots": [s.to_dict() for s in self.slots],
            "batches": [b.to_dict() for b in self.batches],
        }


def parse_publisher_config(raw: dict[str, Any] | None) -> PublisherConfig:
    raw = raw if isinstance(raw, dict) else DEFAULT_PUBLISHER
    slots_raw = raw.get("slots") if raw.get("slots") is not None else DEFAULT_PUBLISHER["slots"]
    batches_raw = raw.get("batches") if raw.get("batches") is not None else DEFAULT_PUBLISHER["batches"]

    slots: list[PublisherSlot] = []
    for item in slots_raw or []:
        if not isinstance(item, dict):
            continue
        sid = int(item.get("slot_id") or 0)
        bid = str(item.get("batch_id") or "").strip()
        if sid and bid:
            slots.append(
                PublisherSlot(
                    slot_id=sid,
                    batch_id=bid,
                    label=str(item.get("label") or bid),
                )
            )

    batches: list[PublisherBatch] = []
    for item in batches_raw or []:
        if not isinstance(item, dict):
            continue
        bid = str(item.get("batch_id") or "").strip()
        if not bid:
            continue
        batches.append(
            PublisherBatch(
                batch_id=bid,
                site_code=str(item.get("site_code") or ""),
                theme_id=str(item.get("theme_id") or ""),
                label=str(item.get("label") or bid),
            )
        )

    if not slots or not batches:
        return parse_publisher_config(DEFAULT_PUBLISHER)

    return PublisherConfig(
        headless=bool(raw.get("headless", True)),
        slots=slots,
        batches=batches,
    )
