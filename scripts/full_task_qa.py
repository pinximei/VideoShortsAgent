#!/usr/bin/env python3
"""一键：重渲 douyin → 打分 → 抽帧 → 离线 A/B → 成片验收。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, timeout: int = 3600) -> int:
    print("+", " ".join(cmd))
    r = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    def _safe_print(text: str) -> None:
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))

    if r.stdout:
        _safe_print(r.stdout[-4000:])
    if r.stderr:
        _safe_print(r.stderr[-1500:])
    return r.returncode


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: full_task_qa.py <task_dir> [--skip-render]")
        return 2
    task_dir = Path(sys.argv[1]).resolve()
    skip_render = "--skip-render" in sys.argv
    py = sys.executable

    if not skip_render:
        rc = _run(
            [py, str(ROOT / "scripts" / "rerender_task_slides.py"), str(task_dir), "douyin"],
            timeout=2400,
        )
        if rc != 0:
            return rc

    for script in (
        "score_task_render.py",
        "extract_score_frames.py",
        "run_douyin_offline_loop.py",
        "verify_post_render.py",
    ):
        extra: list[str] = []
        if script == "run_douyin_offline_loop.py":
            extra = ["--with-video"]
        rc = _run([py, str(ROOT / "scripts" / script), str(task_dir), *extra], timeout=120)
        if rc != 0 and script == "score_task_render.py":
            return rc

    summary = {
        "task_dir": str(task_dir),
        "score": json.loads((task_dir / "RENDER_QUALITY_SCORE.json").read_text(encoding="utf-8-sig"))
        if (task_dir / "RENDER_QUALITY_SCORE.json").is_file()
        else {},
        "verify": json.loads((task_dir / "POST_RENDER_VERIFY.json").read_text(encoding="utf-8-sig"))
        if (task_dir / "POST_RENDER_VERIFY.json").is_file()
        else {},
        "offline": json.loads((task_dir / "OFFLINE_LOOP_REPORT.json").read_text(encoding="utf-8-sig"))
        if (task_dir / "OFFLINE_LOOP_REPORT.json").is_file()
        else {},
    }
    out = task_dir / "FULL_TASK_QA_SUMMARY.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("verify", {}).get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
