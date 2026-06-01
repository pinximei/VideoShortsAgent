#!/usr/bin/env python3
"""从 remotion-dev/skills 同步到 vendor/remotion-best-practices（可提交 Git、可重复更新）。"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "remotion-best-practices"
AGENTS = ROOT / ".agents" / "skills" / "remotion-best-practices"


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)


def main() -> int:
    tmp = ROOT / "vendor" / "_skills_tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    print("[sync] npx skills add remotion-dev/skills ...")
    _run(
        ["npx", "--yes", "skills", "add", "remotion-dev/skills", "--yes"],
        cwd=tmp,
    )

    src = None
    for candidate in (
        tmp / ".agents" / "skills" / "remotion-best-practices",
        AGENTS,
        ROOT / "vendor" / "remotion-best-practices",
    ):
        if (candidate / "SKILL.md").is_file():
            src = candidate
            break

    if not src:
        print("ERROR: remotion-best-practices not found after install")
        return 1

    if VENDOR.exists():
        shutil.rmtree(VENDOR)
    shutil.copytree(src, VENDOR)

    meta = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "source": "https://github.com/remotion-dev/skills",
        "install_cmd": "npx skills add remotion-dev/skills",
    }
    (VENDOR / "VERSION.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "vendor" / "README.md").write_text(
        "# Vendor 官方依赖\n\n"
        "- `remotion-best-practices/`：Remotion Agent Skills（`scripts/sync_remotion_official_skills.py` 更新）\n",
        encoding="utf-8",
    )

    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"[sync] OK -> {VENDOR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
