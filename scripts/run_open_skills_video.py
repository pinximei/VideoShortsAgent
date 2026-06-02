#!/usr/bin/env python3
"""开源多 Skill 编排成片 + 报告（Remotion 官方 skills + 项目 Compose/Render skills）。"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "skills_orchestration"

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "middle"))

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    task_dir = OUT / ts / "task"
    llm_dir = task_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)

    BEST_GV = {
        "douyin": {
            "github_daily_style_id": "G05_dark_top10_rank",
            "voice_content_style_id": "V01_burst_hook_fast",
        },
        "xhs": {
            "github_daily_style_id": "G11_kinetic_word_slam",
            "voice_content_style_id": "V04_minimal_calm",
        },
    }
    brief = {
        "title": "GitHub 日更神器 · Skills 编排演示",
        "hook": "你绝对不知道！昨晚 Star 破万",
        "feed_kind": "github_daily",
        "series": "每天一个GitHub项目",
        "content_key": f"skills_demo_{ts}",
        "talking_points": [
            "多 Skill：Compose + LLM 导演 + Remotion 官方规范",
            "口播与中部屏显由 LLM 分工，图表按 viz_type 可选",
            "抖音/小红书分平台渲染",
        ],
        "cta": "评论区要链接",
        **BEST_GV["douyin"],
    }
    (task_dir / "brief.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    from pipeline.config import load_config
    from python_agent.video_skills_orchestrator import run_full_orchestration

    cfg = load_config(ROOT / "middle" / "config.yaml")
    cfg.render_mode = "slides"
    cfg.render_enabled = True

    print("[open-skills] 编排开始（force_compose + LLM 导演）...")
    brief["_platform_gv"] = BEST_GV
    report = run_full_orchestration(
        task_dir=task_dir,
        brief=brief,
        cfg=cfg,
        platforms=("douyin", "xhs"),
        force_compose=True,
        report_dir=OUT / ts,
    )

    print(f"\n[open-skills] 报告 Markdown: {report['report_md']}")
    print(f"[open-skills] 报告 JSON: {report['report_json']}")
    for pr in report.get("platforms") or []:
        print(f"  {pr.get('platform')}: {pr.get('video')}")

    ok = all(
        any(st.get("ok") for st in (pr.get("steps") or []) if st.get("skill") == "dubbing_and_render_slides")
        for pr in report.get("platforms") or []
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
