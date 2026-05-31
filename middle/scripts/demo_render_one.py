#!/usr/bin/env python3
"""拉一篇 Soul 文章 → LLM 分镜 → Remotion 出小红书 + 抖音视频（本地验收）。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


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


def _ensure_broll(path: Path) -> None:
    from scripts.ensure_broll import ensure_broll

    ensure_broll(path, seconds=60.0)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--render-only", action="store_true", help="仅重渲视频（任务目录已有 llm 分镜）")
    ap.add_argument("--task-dir", type=str, default="", help="如 data/output/838")
    ap.add_argument("--article-id", type=int, default=0, help="指定 Soul 文章 id（如 889）")
    args = ap.parse_args()
    _load_dotenv()
    from pipeline.article_content import article_has_substantive_content
    from pipeline.brief import build_brief
    from pipeline.config import load_config
    from pipeline.media_probe import probe_video_duration
    from pipeline.platform_llm import write_publish_pack
    from pipeline.soul_client import SoulClient
    from pipeline.vsa import render_from_llm_plan

    cfg_path = ROOT / "config.yaml"
    if not cfg_path.is_file():
        print(f"缺少 {cfg_path}，请先复制 config.example.yaml", file=sys.stderr)
        return 1

    cfg = load_config(cfg_path)
    broll = (ROOT / "data/assets/broll_template.mp4").resolve()
    if not (cfg.broll_template or "").strip():
        cfg.broll_template = str(broll)
    _ensure_broll(Path(cfg.broll_template))

    if args.render_only:
        out_dir = Path(args.task_dir or "").resolve()
        if not out_dir.is_dir():
            print("请指定 --task-dir", file=sys.stderr)
            return 1
        broll_sec = probe_video_duration(cfg.broll_template)
        results: dict[str, str] = {}
        for platform in ("xhs", "douyin"):
            print(f"\n[demo] 重渲 {platform} …")
            out = render_from_llm_plan(cfg, out_dir, platform)
            results[platform] = str(out)
        print(json.dumps({"task_dir": str(out_dir), "videos": results}, ensure_ascii=False, indent=2))
        return 0

    client = SoulClient(cfg)
    article = None
    article_id = 0

    if args.article_id > 0:
        full = client.get_article(args.article_id)
        if not full:
            print(f"文章 {args.article_id} 不存在", file=sys.stderr)
            return 1
        ok, reason = article_has_substantive_content(full)
        if not ok:
            print(f"文章 {args.article_id} 无实质正文: {reason}", file=sys.stderr)
            return 1
        article = full
        article_id = args.article_id
        print(f"[demo] 指定文章 id={article_id} title={str(full.get('title') or '')[:60]}")
    else:
        items = client.list_feed()
        if not items:
            print("Soul feed 为空", file=sys.stderr)
            return 1
        for it in items:
            aid = int(it.get("id") or 0)
            if aid <= 0:
                continue
            full = client.get_article(aid)
            if not full:
                continue
            ok, reason = article_has_substantive_content(full)
            if not ok:
                print(f"  跳过 {aid}: {reason}")
                continue
            article = full
            article_id = aid
            print(f"[demo] 选用文章 id={aid} title={str(full.get('title') or '')[:60]}")
            break

    if not article:
        print("未找到有实质正文的文章", file=sys.stderr)
        return 1

    theme_id = "ai_news"
    for t in cfg.themes:
        if t.id == "ai_news":
            theme_id = "ai_news"
            break
    brief = build_brief(article, public_base_url=cfg.public_base_url, theme_id=theme_id)
    out_dir = cfg.output_root / str(article_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    broll_sec = probe_video_duration(cfg.broll_template)
    print(f"[demo] B-roll 时长 {broll_sec:.1f}s，生成文案与分镜…")
    try:
        write_publish_pack(brief, out_dir, cfg=cfg, article=article, broll_seconds=broll_sec)
    except Exception as e:
        print(f"[demo] LLM 不可用 ({e})，改用规则模板 + brief_to_clips")
        from pipeline.publish_pack import write_publish_pack_templates
        from pipeline.platform_llm import write_fallback_video_plans

        write_publish_pack_templates(brief, out_dir)
        cfg.render_allow_template_fallback = True
        write_fallback_video_plans(brief, out_dir, cfg)

    results: dict[str, str] = {}
    for platform in ("xhs", "douyin"):
        print(f"\n[demo] Remotion 渲染 {platform} …")
        try:
            out = render_from_llm_plan(cfg, out_dir, platform)
            results[platform] = str(out)
            print(f"  -> {out}")
        except Exception as e:
            print(f"  [FAIL] {platform}: {e}", file=sys.stderr)
            return 1

    summary = {
        "article_id": article_id,
        "task_dir": str(out_dir),
        "videos": results,
        "manifest": str(out_dir / "videos" / "manifest.json"),
    }
    (out_dir / "demo_result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("\n[demo] 自动验收…")
    try:
        from pipeline.render_verify import run_post_render_verify

        vr = run_post_render_verify(out_dir)
        summary["verify_ok"] = vr.get("ok", False)
    except Exception as ex:
        summary["verify_ok"] = False
        summary["verify_error"] = str(ex)[:200]

    print("\n=== 完成 ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n请本地播放:\n  {results.get('xhs')}\n  {results.get('douyin')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
