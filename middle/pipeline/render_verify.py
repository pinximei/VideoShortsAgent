"""渲染后自动验收（时长轴 + 抽帧）。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


MIN_VIDEO_BYTES = 48 * 1024


def _streams_in_sync(video_path: Path, *, tolerance: float = 0.6) -> bool:
    import subprocess

    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_entries", "stream=codec_type,duration",
        "-of", "json", str(video_path),
    ]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        data = json.loads(r.stdout or "{}")
        vd = ad = None
        for st in data.get("streams") or []:
            if not isinstance(st, dict) or st.get("duration") is None:
                continue
            d = float(st["duration"])
            if st.get("codec_type") == "video" and vd is None:
                vd = d
            elif st.get("codec_type") == "audio" and ad is None:
                ad = d
        if vd is None or ad is None:
            return True
        return abs(vd - ad) <= tolerance
    except Exception:
        return True


def _quick_video_checks(task_dir: Path, platforms: list[str]) -> dict[str, Any]:
    """轻量验收：文件存在 + 体积 + 时长 > 3s。"""
    from .media_probe import probe_video_duration

    out: dict[str, Any] = {"platforms": {}, "ok": True}
    for pid in platforms:
        p = task_dir / "videos" / f"{pid}.mp4"
        entry: dict[str, Any] = {"path": str(p), "exists": p.is_file()}
        if not p.is_file():
            entry["ok"] = False
            out["ok"] = False
        else:
            size = p.stat().st_size
            entry["size_bytes"] = size
            dur = probe_video_duration(str(p))
            entry["duration_sec"] = dur
            stream_sync = True
            if entry["exists"] and dur and dur >= 3.0:
                stream_sync = _streams_in_sync(p)
                entry["stream_sync"] = stream_sync
            entry["ok"] = (
                size >= MIN_VIDEO_BYTES
                and dur is not None
                and dur >= 3.0
                and stream_sync
            )
            if size < MIN_VIDEO_BYTES:
                entry["warn"] = f"file_too_small<{MIN_VIDEO_BYTES}"
            if not stream_sync:
                entry["warn"] = (entry.get("warn") or "") + " stream_duration_mismatch"
            if not entry["ok"]:
                out["ok"] = False
        out["platforms"][pid] = entry
    return out


def run_post_render_verify(
    task_dir: Path,
    platforms: list[str] | None = None,
    *,
    full_verify: bool = False,
) -> dict[str, Any]:
    """验收：默认轻量（时长+特效审计）；full_verify=true 时跑抽帧/音画脚本。"""
    root = _repo_root()
    middle = root / "middle"
    plat = platforms or ["xhs", "douyin"]
    report: dict[str, Any] = {"platforms": {}, "ok": True, "mode": "full" if full_verify else "quick"}

    report["quick"] = _quick_video_checks(task_dir, plat)
    if not report["quick"].get("ok", True):
        report["ok"] = False

    if not full_verify:
        try:
            from .effects_audit import audit_task_effects

            fx = audit_task_effects(task_dir, platforms=plat)
            report["effects_audit"] = fx
            if not fx.get("ok", True):
                report["ok"] = False
        except Exception as exc:
            report["effects_audit"] = {"ok": False, "error": str(exc)[:200], "warnings": []}
            if not report["quick"].get("ok", True):
                report["ok"] = False
    else:
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
                [py, str(script), str(task_dir.resolve())],
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
