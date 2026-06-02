#!/usr/bin/env python3
"""离线 mock 分镜 + 双平台成片，用于确认小红书/抖音视觉与字幕安全区。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "platform_verify"


def _extract_frames(video: Path, out_dir: Path, n: int = 4) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dur_cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-show_entries",
        "format=duration",
        "-of",
        "csv=p=0",
        str(video),
    ]
    r = subprocess.run(dur_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        dur = float((r.stdout or "30").strip())
    except ValueError:
        dur = 30.0
    paths: list[str] = []
    for i in range(n):
        t = max(0.5, dur * (0.15 + 0.7 * i / max(1, n - 1)))
        png = out_dir / f"frame_{i:02d}_{int(t)}s.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(t),
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(png),
            ],
            capture_output=True,
            timeout=60,
        )
        if png.is_file():
            paths.append(str(png))
    return paths


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--douyin-only", action="store_true", help="仅渲染抖音验证片")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "middle"))

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("SLIDES_RENDER_PARALLEL", "0")
    os.environ.setdefault("TTS_WORD_BOUNDARIES", "1")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    task_dir = OUT / ts / "task"
    llm_dir = task_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)

    brief = {
        "title": "OpenHands：AI 编程助手",
        "repo_name": "OpenHands",
        "repo_url": "https://github.com/All-Hands-AI/OpenHands",
        "stars": "1.2万 Star",
        "hook": "",
        "feed_kind": "github_daily",
        "series": "每天一个GitHub项目",
        "content_key": f"platform_verify_{ts}",
        "talking_points": [
            "用自然语言说清你要做什么，它会直接生成可运行的桌面小工具",
            "处理文件和对话都在本机完成，适合合同、表格等不方便上传的资料",
            "适合日报汇总、批量改文件名、表格格式转换这类重复办公活",
        ],
        "cta": "想看同类神器记得关注，下期继续拆趋势项目",
        "platform": "douyin",
        "use_platform_gv_default": True,
    }
    (task_dir / "brief.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    from python_agent.eval_mock_compose import mock_compose_from_brief

    script = mock_compose_from_brief(brief)
    (llm_dir / "slides_script.json").write_text(
        json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    from pipeline.config import load_config
    from pipeline.slides_render import render_slides_video

    cfg = load_config(ROOT / "middle" / "config.yaml")
    cfg.render_mode = "slides"
    cfg.render_enabled = True

    platforms = ("douyin",) if args.douyin_only else ("douyin", "xhs")
    report: dict = {"task_dir": str(task_dir), "platforms": {}, "generated_at": ts}
    for plat in platforms:
        print(f"\n[verify] 渲染 {plat} ...")
        try:
            out = render_slides_video(cfg, task_dir, platform_id=plat)
            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    str(out),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            fmt = {}
            if probe.returncode == 0:
                fmt = json.loads(probe.stdout or "{}").get("format") or {}
            frames = _extract_frames(Path(out), task_dir / "frames" / plat)
            report["platforms"][plat] = {
                "video": str(out),
                "bytes": Path(out).stat().st_size if Path(out).is_file() else 0,
                "duration_sec": float(fmt.get("duration") or 0),
                "frames": frames,
            }
            print(f"  OK {out} ({report['platforms'][plat]['bytes'] // 1024} KB)")
        except Exception as e:
            report["platforms"][plat] = {"error": str(e)}
            print(f"  FAIL {e}")

    verify_r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_slides_output.py"), str(task_dir)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    report["verify_stdout"] = verify_r.stdout[-2000:] if verify_r.stdout else ""
    report["verify_ok"] = verify_r.returncode == 0

    from scripts.verify_post_render import verify_post_render

    post = verify_post_render(task_dir, report=report)
    report["post_render"] = post
    report["verify_ok"] = bool(
        report.get("verify_ok") or post.get("ok", False)
    ) and post.get("ok", False) is not False

    out_json = OUT / ts / "VERIFY_REPORT.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# 双平台成片验证",
        "",
        f"- 任务目录: `{task_dir}`",
        f"- 时间: {ts}",
        "",
    ]
    for plat, row in report.get("platforms", {}).items():
        if row.get("video"):
            md.append(f"## {plat}")
            md.append(f"- 视频: `{row['video']}`")
            md.append(f"- 时长: {row.get('duration_sec', 0):.1f}s")
            for f in row.get("frames") or []:
                md.append(f"- 抽帧: `{f}`")
        else:
            md.append(f"## {plat} — 失败\n- {row.get('error')}")
    (OUT / ts / "README.md").write_text("\n".join(md), encoding="utf-8")

    print(f"\n[verify] 报告: {out_json}")
    if post.get("issues"):
        for x in post["issues"]:
            print(f"  [post_render] {x}")
    ok = all(p.get("video") for p in report.get("platforms", {}).values())
    return 0 if ok and report.get("verify_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
