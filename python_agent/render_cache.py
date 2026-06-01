"""Remotion 单镜渲染缓存（props + 帧数 hash）。"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from typing import Any


def slide_render_cache_key(
    slide: dict[str, Any],
    style: dict[str, Any],
    frames: int,
    sentences: list[dict[str, Any]],
    caption_pages: list[dict[str, Any]],
) -> str:
    payload = {
        "slide": {
            k: slide.get(k)
            for k in sorted(slide.keys())
            if not str(k).startswith("_") and k not in ("image_path",)
        },
        "style": {k: style.get(k) for k in ("accent_color", "text_color", "caption_style", "colors")},
        "frames": frames,
        "sentences": sentences,
        "captionPages": caption_pages,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def cached_video_path(cache_dir: str, key: str) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"slide_{key}.mp4")


def try_copy_cached(cache_dir: str, key: str, dest: str) -> bool:
    src = cached_video_path(cache_dir, key)
    if os.path.isfile(src) and os.path.getsize(src) > 1024:
        shutil.copy2(src, dest)
        return True
    return False


def store_cache(cache_dir: str, key: str, src: str) -> None:
    if not os.path.isfile(src) or os.path.getsize(src) < 1024:
        return
    dest = cached_video_path(cache_dir, key)
    shutil.copy2(src, dest)
