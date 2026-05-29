"""CLI：对已有任务目录执行 VSA（仅 FFmpeg，需 llm/video_clips_*.json）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.config import load_config
from pipeline.vsa import render_from_llm_plan, render_task_videos


def main() -> None:
    p = argparse.ArgumentParser(description="中间层 VSA：按大模型分镜出片")
    p.add_argument("--task-dir", "-t", required=True)
    p.add_argument("--platform", "-p", help="单平台，如 douyin；省略则渲染 config 中全部视频平台")
    p.add_argument("--config", "-c", default="config.yaml")
    args = p.parse_args()

    cfg = load_config(args.config)
    task = Path(args.task_dir)
    if args.platform:
        out = render_from_llm_plan(cfg, task, args.platform)
        print(json.dumps({"platform": args.platform, "path": str(out)}, ensure_ascii=False))
    else:
        print(json.dumps(render_task_videos(cfg, task), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
