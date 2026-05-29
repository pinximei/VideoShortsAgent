from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .job_flow import (
    PUBLISH_CHANNELS,
    STATUS_COMPLETED,
    STATUS_DISCOVERED,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STATUS_READY,
    STATUS_SKIPPED,
    STEP_DONE,
    STEP_READY,
)

# 兼容旧查询
LEGACY_STATUS_MAP = {
    "queued": STATUS_PROCESSING,
    "rendering": STATUS_PROCESSING,
    "rendered": STATUS_READY,
    "packed": STATUS_READY,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class JobStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    content_key TEXT PRIMARY KEY,
                    article_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'discovered',
                    step TEXT NOT NULL DEFAULT '',
                    brief_hash TEXT,
                    soul_snapshot TEXT,
                    brief_json TEXT,
                    output_dir TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
                CREATE INDEX IF NOT EXISTS idx_jobs_article ON jobs(article_id);

                CREATE TABLE IF NOT EXISTS publish_log (
                    content_key TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    note TEXT,
                    PRIMARY KEY (content_key, channel)
                );

                CREATE TABLE IF NOT EXISTS job_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    step TEXT NOT NULL,
                    message TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_job_events_ck ON job_events(content_key);
                """
            )
            cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
            if "step" not in cols:
                conn.execute("ALTER TABLE jobs ADD COLUMN step TEXT NOT NULL DEFAULT ''")
            if "theme_id" not in cols:
                conn.execute("ALTER TABLE jobs ADD COLUMN theme_id TEXT NOT NULL DEFAULT ''")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_theme ON jobs(theme_id)")
            pub_cols = {r[1] for r in conn.execute("PRAGMA table_info(publish_log)").fetchall()}
            if "account_id" not in pub_cols:
                conn.execute("ALTER TABLE publish_log ADD COLUMN account_id TEXT NOT NULL DEFAULT ''")

    def log_event(
        self,
        content_key: str,
        *,
        status: str,
        step: str,
        message: str = "",
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO job_events (content_key, status, step, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (content_key, status, step, message, _utc_now()),
            )

    def advance(
        self,
        content_key: str,
        *,
        status: str,
        step: str,
        message: str = "",
        error: str = "",
        brief_hash: str | None = None,
        brief_json: dict[str, Any] | None = None,
        output_dir: str | None = None,
        theme_id: str | None = None,
    ) -> None:
        self.update_job(
            content_key,
            status=status,
            step=step,
            error=error,
            brief_hash=brief_hash,
            brief_json=brief_json,
            output_dir=output_dir,
            theme_id=theme_id,
        )
        self.log_event(content_key, status=status, step=step, message=message or error)

    def get_job(self, content_key: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE content_key = ?", (content_key,)
            ).fetchone()
            return dict(row) if row else None

    def list_events(self, content_key: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM job_events WHERE content_key = ?
                ORDER BY id DESC LIMIT ?
                """,
                (content_key, limit),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]

    def upsert_discovered(
        self,
        *,
        content_key: str,
        article_id: int,
        snapshot: dict[str, Any],
        theme_id: str = "",
    ) -> bool:
        now = _utc_now()
        snap = json.dumps(snapshot, ensure_ascii=False)
        created = False
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO jobs (content_key, article_id, status, step, theme_id, soul_snapshot, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_key) DO NOTHING
                """,
                (content_key, article_id, STATUS_DISCOVERED, "discover", theme_id, snap, now, now),
            )
            created = cur.rowcount > 0
        if created:
            self.log_event(
                content_key,
                status=STATUS_DISCOVERED,
                step="discover",
                message=f"Soul new article · theme={theme_id or '—'}",
            )
        return created

    def update_job(
        self,
        content_key: str,
        *,
        status: str | None = None,
        step: str | None = None,
        brief_hash: str | None = None,
        brief_json: dict[str, Any] | None = None,
        output_dir: str | None = None,
        error: str | None = None,
        theme_id: str | None = None,
    ) -> None:
        fields: list[str] = []
        values: list[Any] = []
        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if step is not None:
            fields.append("step = ?")
            values.append(step)
        if brief_hash is not None:
            fields.append("brief_hash = ?")
            values.append(brief_hash)
        if brief_json is not None:
            fields.append("brief_json = ?")
            values.append(json.dumps(brief_json, ensure_ascii=False))
        if output_dir is not None:
            fields.append("output_dir = ?")
            values.append(output_dir)
        if error is not None:
            fields.append("error = ?")
            values.append(error)
        if theme_id is not None:
            fields.append("theme_id = ?")
            values.append(theme_id)
        fields.append("updated_at = ?")
        values.append(_utc_now())
        values.append(content_key)
        sql = f"UPDATE jobs SET {', '.join(fields)} WHERE content_key = ?"
        with self._conn() as conn:
            conn.execute(sql, values)

    def list_jobs(
        self,
        statuses: tuple[str, ...] | None = None,
        *,
        theme_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._conn() as conn:
            clauses: list[str] = []
            params: list[Any] = []
            if statuses:
                expanded: list[str] = []
                for s in statuses:
                    expanded.append(s)
                    for old, new in LEGACY_STATUS_MAP.items():
                        if new == s or s == old:
                            expanded.append(old)
                expanded = list(dict.fromkeys(expanded))
                placeholders = ",".join("?" * len(expanded))
                clauses.append(f"status IN ({placeholders})")
                params.extend(expanded)
            if theme_id:
                clauses.append("theme_id = ?")
                params.append(theme_id)
            where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
            sql = f"SELECT * FROM jobs{where} ORDER BY updated_at DESC"
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    def should_skip_render(self, content_key: str, new_hash: str) -> bool:
        job = self.get_job(content_key)
        if not job:
            return False
        st = job.get("status") or ""
        if st not in (STATUS_READY, STATUS_COMPLETED, "packed", "rendered"):
            return False
        return (job.get("brief_hash") or "") == new_hash

    def mark_published(self, content_key: str, channel: str, note: str = "", account_id: str = "") -> bool:
        now = _utc_now()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO publish_log (content_key, channel, published_at, note, account_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(content_key, channel) DO NOTHING
                """,
                (content_key, channel, now, note, account_id),
            )
            created = cur.rowcount > 0
        if created:
            self.log_event(
                content_key,
                status=STATUS_READY,
                step="publish_mark",
                message=f"已标记发布: {channel}",
            )
            self._maybe_complete(content_key)
        return created

    def _maybe_complete(self, content_key: str) -> None:
        if all(self.is_published(content_key, ch) for ch in PUBLISH_CHANNELS):
            self.advance(
                content_key,
                status=STATUS_COMPLETED,
                step=STEP_DONE,
                message="全渠道已标记发布",
            )

    def is_published(self, content_key: str, channel: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM publish_log WHERE content_key = ? AND channel = ?",
                (content_key, channel),
            ).fetchone()
            return row is not None

    def pending_publish(self, channel: str, *, theme_id: str | None = None) -> list[dict[str, Any]]:
        with self._conn() as conn:
            theme_clause = ""
            params: list[Any] = [channel, STATUS_READY]
            if theme_id:
                theme_clause = " AND j.theme_id = ?"
                params.append(theme_id)
            rows = conn.execute(
                f"""
                SELECT j.* FROM jobs j
                LEFT JOIN publish_log p ON p.content_key = j.content_key AND p.channel = ?
                WHERE j.status IN (?, 'packed', 'rendered')
                  AND p.content_key IS NULL
                  {theme_clause}
                ORDER BY j.updated_at DESC
                """,
                tuple(params),
            ).fetchall()
            return [dict(r) for r in rows]

    def count_pending_by_theme_channel(self, theme_ids: list[str], channels: tuple[str, ...]) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {tid: {ch: 0 for ch in channels} for tid in theme_ids}
        for tid in theme_ids:
            for ch in channels:
                out[tid][ch] = len(self.pending_publish(ch, theme_id=tid))
        return out

    def published_channels(self, content_key: str) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT channel FROM publish_log WHERE content_key = ?",
                (content_key,),
            ).fetchall()
            return [r[0] for r in rows]
