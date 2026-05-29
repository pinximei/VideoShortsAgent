from __future__ import annotations

from typing import Any

import httpx

from .config import PipelineConfig


class SoulClient:
    def __init__(self, cfg: PipelineConfig, *, timeout: float = 60.0) -> None:
        self.cfg = cfg
        self.base = cfg.soul_base_url.rstrip("/")
        self.timeout = timeout

    def _get_data(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base}{path}"
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            r = client.get(url, params=params or {})
            r.raise_for_status()
            body = r.json()
        if not isinstance(body, dict):
            raise RuntimeError(f"unexpected response from {url}")
        if body.get("code") != 0:
            raise RuntimeError(f"soul api error: {body.get('message')}")
        return body.get("data")

    def list_feed(self) -> list[dict[str, Any]]:
        params = {
            "feed": self.cfg.soul_feed,
            "page_size": self.cfg.soul_page_size,
            "published_within_days": self.cfg.soul_published_within_days,
        }
        if self.cfg.soul_replication_high_value:
            params["replication_high_value"] = "true"
        data = self._get_data("/api/public/v1/articles/feed", params)
        if isinstance(data, dict):
            items = data.get("items") or []
            return [x for x in items if isinstance(x, dict)]
        return []

    def get_article(self, article_id: int) -> dict[str, Any] | None:
        data = self._get_data(f"/api/public/v1/articles/{article_id}")
        return data if isinstance(data, dict) else None
