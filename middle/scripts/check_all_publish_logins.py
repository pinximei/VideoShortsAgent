#!/usr/bin/env python3
"""一次性检查四渠道登录态（各账号独立 Profile）。

每个渠道在独立子进程中检测，避免浏览器池切换 Profile 时误判。

用法:
  py -3.12 scripts/check_all_publish_logins.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publish_lib import CHANNEL_LABELS, DEFAULT_ACCOUNTS  # noqa: E402
from publisher.profiles import profile_storage_id, resolve_profile_dir  # noqa: E402
from publisher.scripts.registry import BROWSER_CHANNELS  # noqa: E402


def _check_one(account_id: str, *, headed: bool = False) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "check_publisher_login.py"),
        "--account-id",
        account_id,
    ]
    if headed:
        cmd.append("--headed")
    r = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        data = {"logged_in": r.returncode == 0, "error": (r.stderr or r.stdout)[:200]}
    data["_exit"] = r.returncode
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="检查四渠道登录（独立 Profile）")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--json", action="store_true", help="只输出 JSON")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="有界面检测（与登录页一致；请先关闭 open_shared_publish_login 窗口）",
    )
    args = parser.parse_args()

    from pipeline.config import load_config

    cfg = load_config(args.config)
    rows: list[dict] = []
    all_ok = True

    for ch in sorted(BROWSER_CHANNELS):
        aid = DEFAULT_ACCOUNTS[ch]
        acc = next((a for a in cfg.channel_accounts if a.id == aid), None)
        batch_id = ""
        if acc:
            batch_id = (acc.batch_id or "").strip()
            if not batch_id and cfg.publisher.batch_for_site(acc.site_code):
                batch_id = cfg.publisher.batch_for_site(acc.site_code).batch_id
        out = _check_one(aid, headed=args.headed)
        prof = (
            resolve_profile_dir(cfg.data_dir, batch_id or "batch_b", acc, cfg.publisher)
            if acc
            else ""
        )
        shared_id = (
            profile_storage_id(batch_id or "batch_b", acc, cfg.publisher) if acc else ""
        )
        logged = bool(out.get("logged_in"))
        row = {
            "channel": ch,
            "label": CHANNEL_LABELS.get(ch, ch),
            "account_id": aid,
            "logged_in": logged,
            "profile_dir": str(prof),
            "profile_storage_id": shared_id,
            "detail": out.get("detail") or out.get("script"),
        }
        rows.append(row)
        if not logged:
            all_ok = False

    if args.json:
        print(json.dumps({"ok": all_ok, "channels": rows}, ensure_ascii=False, indent=2))
        return 0 if all_ok else 1

    batch = cfg.publisher.batch_by_id("batch_b")
    if batch and batch.shared_profile_id:
        print(
            f"四渠道登录状态（共享浏览器 Profile: {batch.shared_profile_id}）\n"
        )
    else:
        print("四渠道登录状态（每账号独立 Profile）\n")
    for r in rows:
        mark = "已登录" if r["logged_in"] else "未登录"
        print(f"  [{r['label']}] {mark}  account={r['account_id']}")
        print(f"       Profile: {r['profile_dir']}")
    print()
    if all_ok:
        print("全部已登录，可直接 publish_channel / publish_four_reliable。")
    else:
        if batch and batch.shared_profile_id:
            print(
                "未登录：在同一共享浏览器里补登各站：\n"
                "  py -3.12 scripts/open_shared_publish_login.py --wait-seconds 180"
            )
        else:
            print(
                "未登录的渠道请分别扫码：\n"
                "  py -3.12 scripts/ensure_publish_logins.py --wait-seconds 180"
            )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
