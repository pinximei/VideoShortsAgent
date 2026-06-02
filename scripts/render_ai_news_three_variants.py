#!/usr/bin/env python3
"""同一篇爱资讯文章，强制用三套钉死模板各渲一条 douyin 成片对比。"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
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
    ap.add_argument("--article-id", type=int, default=1206)
    args = ap.parse_args()
    _load_dotenv()

    from pipeline.brief import build_brief
    from pipeline.config import load_config
    from pipeline.slides_render import render_slides_video
    from pipeline.soul_client import SoulClient
    from python_agent.pinned_ai_news_template import list_ai_news_variants
    from python_agent.pipeline_media import prefetch_task_cover

    cfg = load_config(MIDDLE / "config.yaml")
    cfg.render_mode = "slides"
    cfg.render_enabled = True
    cfg.render_scene = "ai_news"
    cfg.render_verify_required = False
    cfg.render_platforms = ["douyin"]

    client = SoulClient(cfg)
    article = client.get_article(args.article_id)
    if not article:
        print(f"article {args.article_id} not found", file=sys.stderr)
        return 1

    brief = build_brief(article, public_base_url=cfg.public_base_url, theme_id="ai_news")
    base_brief = brief.to_dict()
    base_brief["feed_kind"] = "news"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = ROOT / "reports" / "ai_news_three_variants" / f"{args.article_id}_{stamp}"
    out_root.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "article_id": args.article_id,
        "title": base_brief.get("title"),
        "generated_at": stamp,
        "variants": [],
        "hot_video_reference": (
            "当前爱资讯成片未自动拉取抖音热点视频作参考；动效来自 motion_templates 目录与 "
            "Remotion TikTok 模板研究。scripts/motion_research/analyze_subtitle_motion.py "
            "可对手工提供的参考片做字幕节奏分析。"
        ),
    }

    variants = list_ai_news_variants()
    if not variants:
        print("no variants in catalog", file=sys.stderr)
        return 1

    for tmpl in variants:
        vid = str(tmpl.get("id") or "")
        label = str(tmpl.get("label") or vid)
        task_dir = out_root / vid
        if task_dir.exists():
            shutil.rmtree(task_dir, ignore_errors=True)
        task_dir.mkdir(parents=True, exist_ok=True)

        brief_dict = dict(base_brief)
        brief_dict["pinned_ai_news_template_id"] = vid
        (task_dir / "brief.json").write_text(
            json.dumps(brief_dict, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        prefetch_task_cover(task_dir, brief_dict)
        cfg.render_visual_style = str(tmpl.get("visual_style") or "warm_gold")

        print(f"\n=== render {vid} ({label}) style={cfg.render_visual_style} ===")
        try:
            video_path = render_slides_video(cfg, task_dir, platform_id="douyin")
            dest = out_root / f"{vid}.mp4"
            shutil.copy2(video_path, dest)
            score = {}
            sp = task_dir / "RENDER_QUALITY_SCORE.json"
            if sp.is_file():
                score = json.loads(sp.read_text(encoding="utf-8-sig"))
            manifest["variants"].append(
                {
                    "template_id": vid,
                    "label": label,
                    "visual_style": tmpl.get("visual_style"),
                    "task_dir": str(task_dir),
                    "video": str(dest),
                    "score": score.get("score"),
                    "grade": score.get("grade"),
                    "pass": score.get("pass"),
                }
            )
            print(f"OK -> {dest}")
        except Exception as exc:  # noqa: BLE001
            manifest["variants"].append(
                {"template_id": vid, "label": label, "error": str(exc)[:400]}
            )
            print(f"FAIL {vid}: {exc}")

    mp = out_root / "MANIFEST.json"
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmanifest: {mp}")
    return 0 if all(v.get("video") for v in manifest["variants"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
