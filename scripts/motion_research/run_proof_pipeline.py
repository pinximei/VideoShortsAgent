#!/usr/bin/env python3
"""一键跑通证明管线。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "motion_research"

STEPS: list[tuple[list[str], str, bool]] = [
    (["export_browser_cookies.py"], "导出 cookie", True),
    (["harvest_bilibili_github.py"], "B站采集 BV", True),
    (
        ["capture_douyin_frames.py", "--force", "--out-subdir", "captures_v2", "--frames", "24", "--interval-ms", "500"],
        "抖音 v2 抽帧",
        True,
    ),
    (["download_reference_media.py"], "下载音轨", True),
    (["analyze_voice_from_captures.py"], "抽帧分析", True),
    (["analyze_voice_from_media.py"], "VTT 分析", True),
    (["analyze_audio_vad.py"], "VAD", True),
    (["batch_asr_dashscope.py"], "DashScope ASR", False),
    (["analyze_subtitle_phash.py"], "phash 字幕切换", True),
    (["build_validated_catalog.py"], "回填 catalog", True),
    (["build_honest_voice_docs.py"], "诚实文档", True),
]


def main() -> int:
    for args, label, fatal in STEPS:
        print(f"\n========== {label} ==========")
        cmd = [sys.executable, str(SCRIPTS / args[0])] + args[1:]
        r = subprocess.run(cmd, cwd=str(ROOT))
        if r.returncode != 0:
            print(f"exit {r.returncode}: {' '.join(args)}")
            if fatal:
                return r.returncode
    print("\nDone → docs/VOICE_CONTENT_PROOF_REPORT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
