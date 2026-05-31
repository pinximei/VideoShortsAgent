#!/usr/bin/env python3
"""调用与控制台相同的 login-check API 逻辑（无需起 HTTP 服务）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--account-id", required=True)
    args = parser.parse_args()

    from pipeline.config import load_config
    from publisher.runner import check_login

    cfg = load_config(args.config)
    acc = next((a for a in cfg.channel_accounts if a.id == args.account_id), None)
    if not acc:
        print(json.dumps({"error": "account not found"}, ensure_ascii=False))
        return 2
    batch_id = (acc.batch_id or "").strip()
    if not batch_id:
        batch = cfg.publisher.batch_for_site(acc.site_code)
        batch_id = batch.batch_id if batch else ""
    if not batch_id:
        print(json.dumps({"error": "no batch_id"}, ensure_ascii=False))
        return 2

    out = check_login(cfg, batch_id, acc)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("logged_in") else 1


if __name__ == "__main__":
    raise SystemExit(main())
