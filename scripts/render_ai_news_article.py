#!/usr/bin/env python3
"""爱资讯单篇：拉 Soul 文章 → brief → 仅渲 douyin slides（不走 B-roll clips LLM）。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIDDLE = ROOT / "middle"
for p in (ROOT, MIDDLE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--article-id", type=int, default=0, help="Soul 文章 ID；0=feed 最新一篇")
    ap.add_argument("--platform", default="douyin", choices=("douyin", "xhs", "both"))
    args = ap.parse_args()
    _load_dotenv()

    from pipeline.brief import build_brief
    from pipeline.config import load_config
    from pipeline.soul_client import SoulClient
    from pipeline.slides_render import render_slides_video
    from python_agent.pipeline_media import prefetch_task_cover

    cfg = load_config(MIDDLE / "config.yaml")
    cfg.render_mode = "slides"
    cfg.render_enabled = True
    cfg.render_scene = "ai_news"
    cfg.render_visual_style = "warm_gold"
    cfg.render_verify_required = False
    if args.platform != "both":
        cfg.render_platforms = [args.platform]

    client = SoulClient(cfg)
    article_id = args.article_id
    if not article_id:
        items = client.list_feed()
        for it in items:
            title = str(it.get("title") or "")
            if "NewsAPI" in title or "connector" in title.lower():
                continue
            article_id = int(it["id"])
            break
        if not article_id and items:
            article_id = int(items[0]["id"])
    if not article_id:
        print("no article in feed", file=sys.stderr)
        return 1

    article = client.get_article(article_id)
    if not article:
        print(f"article {article_id} not found", file=sys.stderr)
        return 1

    brief = build_brief(article, public_base_url=cfg.public_base_url, theme_id="ai_news")
    task_dir = cfg.output_root / str(article_id)
    task_dir.mkdir(parents=True, exist_ok=True)
    prefetch_task_cover(task_dir, brief.to_dict())
    (task_dir / "brief.json").write_text(
        json.dumps(brief.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"article_id={article_id}")
    print(f"title={brief.title}")
    print(f"hook={brief.hook}")
    print(f"feed_kind={brief.feed_kind}")
    print(f"task_dir={task_dir}")

    platforms = ("douyin", "xhs") if args.platform == "both" else (args.platform,)
    for plat in platforms:
        print(f"[render] platform={plat}")
        out = render_slides_video(cfg, task_dir, platform_id=plat)
        print(f"  video={out}")

    score_path = task_dir / "RENDER_QUALITY_SCORE.json"
    if score_path.is_file():
        sc = json.loads(score_path.read_text(encoding="utf-8-sig"))
        print(f"score={sc.get('score')} grade={sc.get('grade')} pass={sc.get('pass')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
