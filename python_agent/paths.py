"""应用路径：用户数据目录、打包资源、FFmpeg。"""
from __future__ import annotations

import os
import sys


def project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_data_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "VideoShortsAgent")
    elif sys.platform == "darwin":
        path = os.path.join(os.path.expanduser("~/Library/Application Support"), "VideoShortsAgent")
    else:
        path = os.path.join(os.path.expanduser("~/.local/share"), "VideoShortsAgent")
    os.makedirs(path, exist_ok=True)
    return path


def bundled_ffmpeg_dir() -> str | None:
    """PyInstaller 或 portable 目录下的 ffmpeg/bin。"""
    roots: list[str] = []
    if is_frozen():
        roots.append(getattr(sys, "_MEIPASS", ""))
    roots.append(project_root())
    for root in roots:
        if not root:
            continue
        for sub in ("resources/ffmpeg/bin", "ffmpeg/bin", "tools/ffmpeg/bin"):
            cand = os.path.join(root, sub)
            if os.path.isfile(os.path.join(cand, "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")):
                return cand
    return None


def prepend_ffmpeg_to_path() -> str | None:
    """若找到内置 FFmpeg，加入 PATH 并返回 bin 目录。"""
    bin_dir = bundled_ffmpeg_dir()
    if not bin_dir:
        return None
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    return bin_dir
