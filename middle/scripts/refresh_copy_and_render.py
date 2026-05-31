#!/usr/bin/env python3
"""刷新 brief + LLM 文案后仅重渲（不重拉长流程）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
for p in (ROOT, REPO):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def _load_dotenv() -> None:
    env_path = REPO / ".env"
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
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--article-id", type=int, required=True)
    args = ap.parse_args()
    _load_dotenv()

    from pipeline.brief import build_brief
    from pipeline.config import load_config
    from pipeline.media_probe import probe_video_duration
    from pipeline.platform_llm import write_publish_pack
    from pipeline.soul_client import SoulClient
    from pipeline.vsa import render_task_videos

    cfg = load_config(ROOT / "config.yaml")
    client = SoulClient(cfg)
    article = client.get_article(args.article_id)
    if not article:
        print(f"article {args.article_id} not found", file=sys.stderr)
        return 1

    brief = build_brief(article, public_base_url=cfg.public_base_url, theme_id="ai_news")
    out_dir = cfg.output_root / str(args.article_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    from scripts.ensure_broll import ensure_broll

    if cfg.broll_template:
        ensure_broll(Path(cfg.broll_template), force=True)
    from python_agent.pipeline_media import prefetch_task_cover

    prefetch_task_cover(out_dir, brief.to_dict())
    (out_dir / "brief.json").write_text(
        json.dumps(brief.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"hook: {brief.hook}")

    broll_sec = probe_video_duration(cfg.broll_template)
    write_publish_pack(brief, out_dir, cfg=cfg, article=article, broll_seconds=broll_sec)

    print("render slides/pipeline…")
    render_task_videos(cfg, out_dir)

    from pipeline.render_verify import run_post_render_verify

    vr = run_post_render_verify(out_dir, full_verify=True)
    print(json.dumps({"verify_ok": vr.get("ok"), "hook": brief.hook}, ensure_ascii=False))
    return 0 if vr.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
