#!/usr/bin/env python3
"""探测 TTS 渠道（Edge + 已配置的 Key 后端）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from dotenv import load_dotenv

load_dotenv(REPO / ".env")

from python_agent.tts_provider import health_check


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="", help="如 zh-CN-YunxiNeural")
    args = ap.parse_args()
    report = health_check(args.voice or None)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
