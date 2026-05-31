"""发布质量规则（门禁 + quality_audit 共用）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

NEWS_MIN_CLIPS = 3
APPS_MIN_CLIPS = 2
MIN_DURATION_SEC = 34.0
MAX_DURATION_SEC = 56.0
HOOK_FRAME_TIMES = (0.0, 3.0, 8.0)
MIN_HOOK_LUMA = 8.0


def min_clips_for_feed(feed_kind: str) -> int:
    return NEWS_MIN_CLIPS if (feed_kind or "").strip().lower() == "news" else APPS_MIN_CLIPS


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _hook_score(text: str) -> tuple[int, list[str]]:
    import re

    issues: list[str] = []
    score = 10
    t = (text or "").strip()
    if len(t) < 6:
        issues.append("钩子过短")
        score -= 4
    if len(t) > 28:
        issues.append(f"钩子 {len(t)} 字，建议 ≤28")
        score -= 2
    if not re.search(r"[？?]", t) and not re.search(r"\d", t):
        issues.append("缺少疑问或数字")
        score -= 3
    return max(0, score), issues


def evaluate_task_quality(
    task_dir: Path,
    *,
    platforms: list[str] | None = None,
    feed_kind: str = "news",
) -> dict[str, Any]:
    """返回 ok / issues，供门禁与 quality_audit 使用。"""
    task_dir = task_dir.resolve()
    plat = platforms or ["douyin", "xhs"]
    min_clips = min_clips_for_feed(feed_kind)
    issues: list[str] = []

    brief = _load_json(task_dir / "brief.json")
    fk = str(brief.get("feed_kind") or feed_kind or "news")
    min_clips = min_clips_for_feed(fk)

    hook = str(brief.get("hook") or "")
    hs, hi = _hook_score(hook)
    if hs < 7:
        issues.extend([f"brief.hook: {x}" for x in hi])

    copy = _load_json(task_dir / "llm" / "platform_copy.json")
    for pid in plat:
        block = copy.get(pid) if isinstance(copy, dict) else None
        if not isinstance(block, dict):
            issues.append(f"{pid}: platform_copy 缺失")
            continue
        clips = block.get("clips") or []
        if len(clips) < min_clips:
            issues.append(f"{pid}: clips={len(clips)} < min {min_clips}")
        if not block.get("effects", {}).get("intro_card"):
            issues.append(f"{pid}: intro_card 未启用")

    durations: dict[str, float] = {}
    for pid in plat:
        p = task_dir / "videos" / f"{pid}.mp4"
        if not p.is_file():
            issues.append(f"{pid}: 缺少成片")
            continue
        try:
            from .media_probe import probe_video_duration

            dur = probe_video_duration(str(p))
            if dur:
                durations[pid] = float(dur)
                if dur < MIN_DURATION_SEC:
                    issues.append(f"{pid}: 时长 {dur:.1f}s < {MIN_DURATION_SEC}s")
                elif dur > MAX_DURATION_SEC:
                    issues.append(f"{pid}: 时长 {dur:.1f}s > {MAX_DURATION_SEC}s（偏长）")
        except Exception as exc:
            issues.append(f"{pid}: 时长探测失败 {exc}")

    hook_frames = _load_json(task_dir / "verify_report.json").get("hook_frames") or {}
    for pid in plat:
        hf = hook_frames.get(pid) if isinstance(hook_frames, dict) else None
        if isinstance(hf, dict) and hf.get("ok") is False:
            issues.append(f"{pid}: 开场抽帧异常")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "min_clips": min_clips,
        "durations": durations,
        "brief_hook_score": hs,
    }


def capture_hook_frames(task_dir: Path, platforms: list[str]) -> dict[str, Any]:
    """0s/3s/8s 抽帧写入 verify_report，供评审无需打开 mp4。"""
    import hashlib
    import subprocess

    out_root = task_dir / "verify_frames" / "hook"
    result: dict[str, Any] = {"ok": True, "platforms": {}}

    for pid in platforms:
        video = task_dir / "videos" / f"{pid}.mp4"
        entry: dict[str, Any] = {"frames": {}, "ok": True}
        if not video.is_file():
            entry["ok"] = False
            entry["error"] = "missing_video"
            result["ok"] = False
            result["platforms"][pid] = entry
            continue
        for t in HOOK_FRAME_TIMES:
            frame_path = out_root / pid / f"t{int(t)}.jpg"
            frame_path.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                "ffmpeg", "-y", "-ss", str(t), "-i", str(video),
                "-frames:v", "1", "-q:v", "2", str(frame_path),
            ]
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=30)
                ok = r.returncode == 0 and frame_path.is_file() and frame_path.stat().st_size > 3000
            except Exception:
                ok = False
            luma = _mean_luma(frame_path) if ok else 0.0
            fh = ""
            if ok:
                h = hashlib.md5()
                with open(frame_path, "rb") as f:
                    h.update(f.read(65536))
                fh = h.hexdigest()[:12]
            entry["frames"][f"{t}s"] = {
                "path": str(frame_path.relative_to(task_dir)) if ok else "",
                "hash": fh,
                "luma": round(luma, 1),
                "ok": ok and luma >= MIN_HOOK_LUMA,
            }
            if not entry["frames"][f"{t}s"]["ok"]:
                entry["ok"] = False
                result["ok"] = False
        result["platforms"][pid] = entry
    return result


def _mean_luma(path: Path) -> float:
    import subprocess

    if not path.is_file():
        return 0.0
    try:
        r = subprocess.run(
            [
                "ffmpeg", "-i", str(path), "-vf", "scale=64:114,format=gray",
                "-f", "rawvideo", "-pix_fmt", "gray", "-frames:v", "1", "-",
            ],
            capture_output=True,
            timeout=15,
        )
        if r.returncode != 0 or not r.stdout:
            return 0.0
        data = r.stdout
        return sum(data) / len(data) if data else 0.0
    except Exception:
        return 0.0
