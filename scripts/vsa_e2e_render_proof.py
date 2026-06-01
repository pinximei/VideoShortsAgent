#!/usr/bin/env python3
"""
VSA 端到端成片证明：真实生成 mp4 + ffprobe + 文件哈希，写入 reports/。

用法:
  py -3 scripts/vsa_e2e_render_proof.py
  py -3 scripts/vsa_e2e_render_proof.py --skip-tts   # 仅验证渲染链（无配音）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_BASE = ROOT / "reports" / "vsa_e2e_proof"

# Windows 控制台默认 GBK，避免 RenderSkill/DubbingSkill 打印 Unicode 导致成片中断
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _ffprobe(path: Path) -> dict:
    p = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if p.returncode != 0:
        return {"error": (p.stderr or "")[-500:]}
    return json.loads(p.stdout or "{}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-tts", action="store_true", help="跳过 TTS（仍产出静音成片）")
    ap.add_argument("--platform", default="douyin", choices=("douyin", "xhs"))
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = REPORT_BASE / ts
    task_dir = report_dir / "task"
    llm_dir = task_dir / "llm"
    videos_dir = task_dir / "videos"
    llm_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    log_lines: list[str] = []

    def log(msg: str) -> None:
        print(msg)
        log_lines.append(msg)

    # 1) B-roll
    import importlib.util

    _eb_spec = importlib.util.spec_from_file_location(
        "ensure_broll", ROOT / "middle" / "scripts" / "ensure_broll.py"
    )
    _eb = importlib.util.module_from_spec(_eb_spec)
    _eb_spec.loader.exec_module(_eb)
    ensure_broll = _eb.ensure_broll

    broll = ROOT / "data" / "assets" / "broll_template.mp4"
    log(f"[1/5] 生成/复用 B-roll: {broll}")
    ensure_broll(broll, seconds=25.0)
    broll_stat = {
        "path": str(broll),
        "bytes": broll.stat().st_size,
        "sha256": _sha256_file(broll),
    }

    # 2) 最小分镜 plan（口播足够长，避免「几个字」）
    clips = [
        {
            "start": 0.0,
            "end": 8.0,
            "tts_text": "别划走，今天这个 GitHub 项目 Star 涨了一万，三分钟讲清它为什么火。",
            "hook_text": "GitHub爆款",
            "caption_style": "spring",
            "transition_to_next": "slideup",
        },
        {
            "start": 8.0,
            "end": 18.0,
            "tts_text": "它能自动抓趋势、生成短视频脚本，还支持一键配音，适合日更科技号。",
            "hook_text": "日更神器",
            "caption_style": "spring",
            "transition_to_next": "fade",
        },
        {
            "start": 18.0,
            "end": 24.0,
            "tts_text": "链接在评论区，点个关注，明天继续拆榜。",
            "hook_text": "关注",
            "caption_style": "spring",
            "transition_to_next": "fade",
        },
    ]
    plan_path = llm_dir / f"video_clips_{args.platform}.json"
    plan = {
        "clips": clips,
        "effects": {"preset": "活力", "use_remotion": True, "caption_style": "spring"},
        "platform": args.platform,
        "source": "e2e_proof",
    }
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    brief = {
        "title": "VSA E2E 证明",
        "hook": clips[0]["tts_text"],
        "feed_kind": "github_daily",
        "platform": args.platform,
        "voice_content_style_id": "V01_burst_hook_fast",
    }
    (task_dir / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    tts_chars = sum(len(c["tts_text"]) for c in clips)
    log(f"[2/5] 分镜 plan: {len(clips)} 镜, 口播共 {tts_chars} 字 → {plan_path}")

    # 3) 渲染
    out_mp4 = videos_dir / f"{args.platform}.mp4"
    log(f"[3/5] 调用 vsa_render.render_from_plan → {out_mp4} (skip_tts={args.skip_tts})")
    sys.path.insert(0, str(ROOT))
    from python_agent.vsa_render import render_from_plan

    t0 = datetime.now(timezone.utc)
    try:
        result = render_from_plan(
            clips=clips,
            broll_path=str(broll),
            output_path=str(out_mp4),
            platform=args.platform,
            skip_tts=args.skip_tts,
            task_dir=str(task_dir),
            feed_kind="github_daily",
            use_remotion=True,
        )
    except Exception as exc:
        import traceback

        err_path = report_dir / "RENDER_ERROR.txt"
        err_path.write_text(traceback.format_exc(), encoding="utf-8")
        (report_dir / "console.log").write_text("\n".join(log_lines), encoding="utf-8")
        log(f"FAIL: {exc}")
        return 1
    t1 = datetime.now(timezone.utc)

    if not out_mp4.is_file() or out_mp4.stat().st_size < 10000:
        log(f"FAIL: 输出不存在或过小 ({out_mp4})")
        return 1

    # 4) ffprobe
    log("[4/5] ffprobe 验证输出…")
    probe = _ffprobe(out_mp4)
    fmt = probe.get("format") or {}
    duration = float(fmt.get("duration") or 0)
    video_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]

    # 5) git + 报告
    git_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    ).stdout.strip()

    proof = {
        "generated_at": t1.isoformat(),
        "started_at": t0.isoformat(),
        "elapsed_sec": round((t1 - t0).total_seconds(), 2),
        "git_head": git_head,
        "skip_tts": args.skip_tts,
        "platform": args.platform,
        "tts_total_chars": tts_chars,
        "broll": broll_stat,
        "output": {
            "path": str(out_mp4.resolve()),
            "bytes": out_mp4.stat().st_size,
            "sha256": _sha256_file(out_mp4),
            "duration_sec": duration,
            "has_video": len(video_streams) > 0,
            "has_audio": len(audio_streams) > 0,
        },
        "render_result": result,
        "log": log_lines,
    }
    (report_dir / "PROOF.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    (report_dir / "ffprobe.json").write_text(json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8")
    (report_dir / "console.log").write_text("\n".join(log_lines), encoding="utf-8")

    md = [
        "# VSA 端到端成片证明",
        "",
        f"- 时间 UTC: {proof['generated_at']}",
        f"- Git: `{git_head}`",
        f"- 耗时: {proof['elapsed_sec']}s",
        f"- skip_tts: {args.skip_tts}",
        "",
        "## 输出视频（真实文件）",
        "",
        f"| 字段 | 值 |",
        f"|------|-----|",
        f"| 路径 | `{proof['output']['path']}` |",
        f"| 大小 | **{proof['output']['bytes']:,}** bytes |",
        f"| SHA256 | `{proof['output']['sha256']}` |",
        f"| 时长 | **{duration:.2f}s** |",
        f"| 有视频轨 | {proof['output']['has_video']} |",
        f"| 有音频轨 | {proof['output']['has_audio']} |",
        "",
        "## 复现",
        "",
        "```powershell",
        "cd D:\\VideoShortsAgent",
        "py -3 scripts/vsa_e2e_render_proof.py",
        "```",
        "",
        "证据目录: `" + str(report_dir) + "`",
    ]
    (report_dir / "PROOF.md").write_text("\n".join(md), encoding="utf-8")

    log(f"[5/5] OK: {out_mp4.stat().st_size:,} bytes, {duration:.2f}s, sha256={proof['output']['sha256'][:16]}…")
    log(f"报告: {report_dir / 'PROOF.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
