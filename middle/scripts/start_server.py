#!/usr/bin/env python3
"""启动 Pipeline API + 静态前端（缺 dist 时尝试 npm build）。"""
from __future__ import annotations

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"


def _ensure_frontend() -> None:
    if DIST.is_dir() and (DIST / "index.html").is_file():
        return
    print("frontend/dist 不存在，正在构建界面…")
    if not (FRONTEND / "package.json").is_file():
        raise SystemExit("缺少 frontend/package.json")
    subprocess.run(["npm", "install"], cwd=FRONTEND, check=True, shell=True)
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND, check=True, shell=True)
    if not DIST.is_dir():
        raise SystemExit("前端构建失败")


def _load_dotenv() -> None:
    import os

    env_path = ROOT.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument(
        "--no-scheduler",
        action="store_true",
        help="不启动内置 7×24 调度（仅 API/UI）",
    )
    args = parser.parse_args()
    _load_dotenv()
    if args.no_scheduler:
        import os

        os.environ["PIPELINE_NO_SCHEDULER"] = "1"
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    vsa_root = ROOT.parent
    if str(vsa_root) not in sys.path:
        sys.path.insert(0, str(vsa_root))
    if not args.skip_build:
        try:
            _ensure_frontend()
        except subprocess.CalledProcessError as e:
            raise SystemExit(f"前端构建失败: {e}") from e
    url = f"http://{args.host}:{args.port}/"
    if not args.no_browser:
        webbrowser.open(url)
    sched = "关闭" if args.no_scheduler else "开启（7×24）"
    print(f"Pipeline 界面: {url}")
    print(f"内置调度: {sched} — 配置见 config.yaml schedule.service")
    uvicorn.run("server.app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
