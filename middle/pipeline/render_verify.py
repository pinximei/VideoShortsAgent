"""渲染后自动验收（时长轴 + 抽帧）。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_post_render_verify(task_dir: Path, platforms: list[str] | None = None) -> dict[str, Any]:
    """调用 middle/scripts 验收脚本，返回汇总。"""
    root = _repo_root()
    middle = root / "middle"
    plat = platforms or ["xhs", "douyin"]
    report: dict[str, Any] = {"platforms": {}, "ok": True}

    av_script = middle / "scripts" / "verify_av_sync.py"
    vis_script = middle / "scripts" / "verify_video_visual.py"
    import os

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    py = sys.executable

    for script, key in ((av_script, "av_sync"), (vis_script, "visual")):
        if not script.is_file():
            continue
        r = subprocess.run(
            [py, str(script)],
            cwd=str(middle),
            capture_output=True,
            text=True,
            timeout=180,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        report[key] = {
            "exit_code": r.returncode,
            "stdout_tail": (r.stdout or "")[-2000:],
            "stderr_tail": (r.stderr or "")[-800:],
        }
        if r.returncode != 0:
            report["ok"] = False

    try:
        from .effects_audit import audit_task_effects

        fx = audit_task_effects(task_dir, platforms=plat)
        report["effects_audit"] = fx
        if not fx.get("ok", True):
            report["ok"] = False
    except Exception as exc:
        report["effects_audit"] = {"ok": False, "error": str(exc)[:200]}
        report["ok"] = False

    manifest = task_dir / "videos" / "manifest.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["verify"] = report
        manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    verify_path = task_dir / "verify_report.json"
    verify_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
