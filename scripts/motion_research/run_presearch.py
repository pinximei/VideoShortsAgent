#!/usr/bin/env python3
"""一键跑动效预研：分析本地样本 + 汇总 references.yaml + 写报告索引。"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "research" / "motion" / "refs"
REPORTS = ROOT / "research" / "motion" / "reports"
ANALYZE = ROOT / "scripts" / "motion_research" / "analyze_subtitle_motion.py"


def main() -> int:
    videos = sorted(REFS.glob("*.mp4"))
    if not videos:
        print(f"No mp4 in {REFS}; download samples first.", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(ANALYZE), *[str(v) for v in videos]]
    print(" ".join(cmd))
    subprocess.check_call(cmd)

    latest = sorted(REPORTS.glob("subtitle_motion_*.json"))[-1]
    data = json.loads(latest.read_text(encoding="utf-8"))

    index = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "latest_analysis": str(latest),
        "samples": [r["video"] for r in data.get("reports", [])],
        "report_path": str(ROOT / "docs" / "MOTION_PRESEARCH_REPORT.md"),
    }
    idx_path = ROOT / "research" / "motion" / "index.json"
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"index: {idx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
