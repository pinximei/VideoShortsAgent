#!/usr/bin/env python3
"""初始化「爱资讯」单主题：固定账号 ID + 站点/批次，便于按 ID 登录浏览器。

固定 ID（请勿随意改，Profile 目录与之一一对应）:
  acc_ai_news_douyin
  acc_ai_news_xhs
  acc_ai_news_toutiao
  acc_ai_news_douban

用法: py -3.12 scripts/init_ai_news_accounts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SITE_CODE = "ai-trends-news"
THEME_ID = "ai_news"
BATCH_ID = "batch_b"

ACCOUNTS = (
    ("acc_ai_news_douyin", "douyin", "抖音 · 爱资讯"),
    ("acc_ai_news_xhs", "xhs", "小红书 · 爱资讯"),
    ("acc_ai_news_toutiao", "toutiao", "头条 · 爱资讯"),
    ("acc_ai_news_douban", "douban", "豆瓣 · 爱资讯"),
)


def main() -> int:
    from pipeline.config_store import read_yaml_dict, update_config_sections

    cfg_path = ROOT / "config.yaml"
    if not cfg_path.is_file():
        print(f"ERROR: 缺少 {cfg_path}", file=sys.stderr)
        return 2

    channel_accounts = [
        {
            "id": aid,
            "site_code": SITE_CODE,
            "channel_id": ch,
            "batch_id": BATCH_ID,
            "label": label,
            "handle": "",
            "profile_url": "",
            "login_hint": "",
            "note": "爱资讯固定账号 ID；抖音/小红书用 open_platform_login.py 登录",
            "enabled": True,
            "is_primary": True,
        }
        for aid, ch, label in ACCOUNTS
    ]

    raw = read_yaml_dict(cfg_path)
    pub = raw.get("publisher") if isinstance(raw.get("publisher"), dict) else {}
    batches = list(pub.get("batches") or [])
    if not any(isinstance(b, dict) and b.get("batch_id") == BATCH_ID for b in batches):
        batches.append(
            {
                "batch_id": BATCH_ID,
                "site_code": SITE_CODE,
                "theme_id": THEME_ID,
                "label": "爱资讯主体",
            }
        )
    slots = list(pub.get("slots") or [])
    if not any(isinstance(s, dict) and s.get("batch_id") == BATCH_ID for s in slots):
        slots.append({"slot_id": 2, "batch_id": BATCH_ID, "label": "爱资讯 · 单主题"})
    pub.setdefault("headless", True)
    pub["batches"] = batches
    pub["slots"] = slots

    update_config_sections(
        cfg_path,
        soul={**(raw.get("soul") or {}), "feed": "news"},
        filter={"feed_kinds": ["news"], "min_worth_score": 5},
        sites=[
            {
                "code": SITE_CODE,
                "label": "AI 资讯站（爱资讯）",
                "description": "Soul 资讯泳道，单主题试运行",
                "theme_id": THEME_ID,
                "base_url": "https://ai-trends.news",
            }
        ],
        channel_accounts=channel_accounts,
        publisher=pub,
    )

    print("已写入 config.yaml：")
    print(f"  主题 theme_id={THEME_ID}  site={SITE_CODE}  batch={BATCH_ID}")
    print("  Soul 拉取 feed=news，filter 仅 news")
    print("\n固定账号 ID（登录浏览器时用 --account-id）：")
    for aid, ch, label in ACCOUNTS:
        login = " ← 先登录" if ch in ("douyin", "xhs") else "（图文，浏览器手工发）"
        print(f"  {aid}  [{ch}] {label}{login}")
    print("\n下一步:")
    print(f"  py -3.12 scripts/open_platform_login.py --account-id acc_ai_news_douyin")
    print(f"  py -3.12 scripts/open_platform_login.py --account-id acc_ai_news_xhs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
