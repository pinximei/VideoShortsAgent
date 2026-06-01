#!/usr/bin/env python3
"""仅重渲染已有 task（复用 TTS/剧本，跳过 Compose）。"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: py -3 scripts/rerender_task_slides.py <task_dir> [douyin|xhs|both]")
        return 2
    task_dir = Path(sys.argv[1]).resolve()
    plat_arg = (sys.argv[2] if len(sys.argv) > 2 else "both").lower()
    platforms = ("douyin", "xhs") if plat_arg == "both" else (plat_arg,)

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "middle"))

    from pipeline.config import load_config
    from pipeline.slides_render import render_slides_video

    cfg = load_config(ROOT / "middle" / "config.yaml")
    cfg.render_mode = "slides"
    cfg.render_enabled = True

    for plat in platforms:
        work = task_dir / "videos" / f"_slides_work_{plat}"
        if work.is_dir():
            shutil.rmtree(work, ignore_errors=True)
        print(f"[rerender] platform={plat}")
        out = render_slides_video(cfg, task_dir, platform_id=plat)
        print(f"  -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
