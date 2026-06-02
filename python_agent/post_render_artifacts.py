"""渲染成功后自动落盘：分数、抽帧、验收摘要。"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _run_script(name: str, task_dir: Path, *extra: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    cmd = ["py", "-3.12", str(root / "scripts" / name), str(task_dir), *extra]
    try:
        r = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        return {"exit_code": r.returncode, "stdout": (r.stdout or "")[-2000:]}
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return {"exit_code": -1, "error": str(exc)}


def write_post_render_bundle(
    task_dir: Path,
    *,
    platform: str = "douyin",
    slides: list[dict[str, Any]] | None = None,
    gate: dict[str, Any] | None = None,
    brief: dict[str, Any] | None = None,
) -> Path:
    """写入 RENDER_QUALITY_SCORE、抽帧、POST_RENDER_VERIFY、FULL_TASK_QA_SUMMARY。"""
    task_dir = task_dir.resolve()
    from python_agent.render_quality_score import score_douyin_render, write_task_score

    if platform == "douyin" and slides is not None:
        video = task_dir / "videos" / "douyin.mp4"
        score = score_douyin_render(
            slides,
            brief=brief,
            gate=gate or {},
            video_path=video if video.is_file() else None,
        )
        (task_dir / "RENDER_QUALITY_SCORE.json").write_text(
            json.dumps(score, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        write_task_score(task_dir, platform=platform, brief=brief)

    if (task_dir / "videos" / f"{platform}.mp4").is_file():
        _run_script("extract_score_frames.py", task_dir, platform)

    verify: dict[str, Any] = {}
    vr = _run_script("verify_post_render.py", task_dir)
    vp = task_dir / "POST_RENDER_VERIFY.json"
    if vp.is_file():
        verify = json.loads(vp.read_text(encoding="utf-8-sig"))
    elif vr.get("exit_code") != 0:
        verify = {"ok": False, "error": vr.get("stdout") or vr.get("error")}

    score_data = json.loads(
        (task_dir / "RENDER_QUALITY_SCORE.json").read_text(encoding="utf-8-sig")
    )
    summary = {
        "task_dir": str(task_dir),
        "platform": platform,
        "score": score_data,
        "verify": verify,
        "video": str(task_dir / "videos" / f"{platform}.mp4"),
    }
    path = task_dir / "FULL_TASK_QA_SUMMARY.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
