#!/usr/bin/env python3
"""对 task 的 plan / 门禁 / 成片打分，写入 RENDER_QUALITY_SCORE.json。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: score_task_render.py <task_dir> [douyin|xhs]")
        return 2
    task_dir = Path(sys.argv[1]).resolve()
    platform = (sys.argv[2] if len(sys.argv) > 2 else "douyin").lower()
    sys.path.insert(0, str(ROOT))

    from python_agent.render_quality_score import write_task_score

    path = write_task_score(task_dir, platform=platform)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0 if data.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
