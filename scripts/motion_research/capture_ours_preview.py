#!/usr/bin/env python3
"""渲染我方 Remotion 样片并抽关键帧，供与对标对比。"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REMOTION = ROOT / "remotion_effects"
OURS = ROOT / "research" / "motion" / "github_daily" / "ours"
PREVIEW_PROPS = ROOT / "research" / "motion" / "github_daily" / "ours" / "preview_title_props.json"


def main() -> int:
    OURS.mkdir(parents=True, exist_ok=True)
    out_mp4 = OURS / "preview_title_tiktok.mp4"
    if not out_mp4.is_file():
        cmd = [
            "npx", "remotion", "render", "src/index.tsx", "TitleCard",
            str(out_mp4),
            f"--props={PREVIEW_PROPS}",
            "--width=1080", "--height=1920", "--frames=0-89",
        ]
        subprocess.check_call(cmd, cwd=str(REMOTION), shell=True)

    kf_dir = OURS / "keyframes"
    kf_dir.mkdir(exist_ok=True)
    for i, sec in enumerate([0, 0.5, 1.0, 1.5, 2.0, 2.5]):
        out_png = kf_dir / f"key_{i:02d}_{int(sec*10)}s.png"
        subprocess.run(
            [
                "ffmpeg", "-y", "-ss", str(sec), "-i", str(out_mp4),
                "-vframes", "1", "-q:v", "2", str(out_png),
            ],
            check=False,
            capture_output=True,
        )

    manifest = {
        "video": str(out_mp4.relative_to(ROOT)).replace("\\", "/"),
        "keyframes": [str(p.relative_to(ROOT)).replace("\\", "/") for p in sorted(kf_dir.glob("*.png"))],
        "props": str(PREVIEW_PROPS.relative_to(ROOT)).replace("\\", "/"),
    }
    (OURS / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
