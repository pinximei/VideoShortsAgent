"""video_orchestrate Skill 执行器。"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def execute(args: dict, context: dict) -> str:
    root = Path(context.get("repo_root") or Path(__file__).resolve().parents[2])
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "middle"))

    task_dir = Path(args.get("task_dir") or context.get("task_dir") or "")
    if not task_dir.is_dir():
        return f"错误：task_dir 不存在: {task_dir}"

    brief_path = task_dir / "brief.json"
    if not brief_path.is_file():
        return f"错误：缺少 brief.json: {brief_path}"

    brief = json.loads(brief_path.read_text(encoding="utf-8-sig"))
    platforms_raw = (args.get("platforms") or "douyin,xhs").strip()
    platforms = tuple(p.strip() for p in platforms_raw.split(",") if p.strip())

    from pipeline.config import load_config
    from python_agent.video_skills_orchestrator import run_full_orchestration

    cfg_path = root / "middle" / "config.yaml"
    cfg = load_config(cfg_path)
    cfg.render_mode = "slides"
    cfg.render_enabled = True

    report = run_full_orchestration(
        task_dir=task_dir,
        brief=brief,
        cfg=cfg,
        platforms=platforms,
        force_compose=True,
        report_dir=task_dir.parent,
    )
    return json.dumps(
        {
            "report_md": report.get("report_md"),
            "report_json": report.get("report_json"),
            "videos": [p.get("video") for p in report.get("platforms") or []],
        },
        ensure_ascii=False,
        indent=2,
    )
