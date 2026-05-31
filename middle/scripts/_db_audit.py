#!/usr/bin/env python3
"""一次性审计 pipeline.db（供 agent 验证用）。"""
import json
import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "data" / "pipeline.db"
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
print("=== jobs by status ===")
for r in conn.execute("SELECT status, COUNT(*) n FROM jobs GROUP BY status ORDER BY n DESC"):
    print(f"  {r['status']}: {r['n']}")
print("\n=== recent jobs ===")
for r in conn.execute(
    "SELECT article_id, status, step, theme_id, updated_at, substr(error,1,120) err FROM jobs ORDER BY updated_at DESC LIMIT 15"
):
    print(dict(r))
for ck in ("aisoul:article:889", "aisoul:article:838"):
    print(f"\n=== events {ck} ===")
    for r in conn.execute(
        "SELECT status, step, message, created_at FROM job_events WHERE content_key=? ORDER BY id",
        (ck,),
    ):
        print(f"  {r['created_at']} [{r['status']}/{r['step']}] {(r['message'] or '')[:100]}")
conn.close()
