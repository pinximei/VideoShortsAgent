"""本地裁剪：仅 FFmpeg，无需 LLM API。"""
from __future__ import annotations

import os
import re
import subprocess
import uuid

from .licensing import record_export
from .skills.render_skill import RenderSkill


def parse_segments(text: str) -> list[dict]:
    """
    解析时间段，每行一个，格式示例：
      0:30-1:05
      1:20.5 - 2:00
      90-120   （秒）
    """
    segments: list[dict] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(
            r"^(\d+(?:\.\d+)?|\d+:\d+(?::\d+)?(?:\.\d+)?)\s*[-~–—]\s*"
            r"(\d+(?:\.\d+)?|\d+:\d+(?::\d+)?(?:\.\d+)?)$",
            line,
        )
        if not m:
            raise ValueError(f"无法解析时间段: {line}")
        segments.append({"start": _to_seconds(m.group(1)), "end": _to_seconds(m.group(2))})
    if not segments:
        raise ValueError("请至少填写一行时间段，例如 0:30-1:05")
    for seg in segments:
        if seg["end"] <= seg["start"]:
            raise ValueError(f"结束时间必须大于开始: {seg['start']} -> {seg['end']}")
    return segments


def _to_seconds(token: str) -> float:
    token = token.strip()
    if ":" not in token:
        return float(token)
    parts = token.split(":")
    parts = [float(p) for p in parts]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"无效时间: {token}")


def process_manual_clip(
    video_path,
    segments_text: str,
    vertical_9_16: bool = False,
) -> tuple[str, str | None]:
    """
    返回 (status_markdown, output_video_path)
    """
    if isinstance(video_path, dict):
        video_path = video_path.get("video", video_path.get("name", ""))
    if not video_path or not os.path.isfile(video_path):
        return "请先上传本地视频文件", None

    try:
        clips = parse_segments(segments_text)
    except ValueError as e:
        return f"❌ {e}", None

    task_dir = os.path.join("output", f"manual_{uuid.uuid4().hex[:8]}")
    os.makedirs(task_dir, exist_ok=True)

    renderer = RenderSkill()
    try:
        out = renderer.execute(video_path, {"clips": clips}, task_dir)
    except Exception as e:
        return f"❌ 裁剪失败: {e}", None

    if not out or not os.path.isfile(out):
        return "❌ 未生成输出文件，请检查 FFmpeg 是否可用", None

    if vertical_9_16:
        cropped = os.path.join(task_dir, "output_vertical.mp4")
        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                out,
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-c:a",
                "copy",
                cropped,
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode == 0 and os.path.isfile(cropped):
            out = cropped

    out = record_export(out, feature="manual_clip")
    size_mb = os.path.getsize(out) / (1024 * 1024)
    return (
        f"✅ 已生成 {len(clips)} 段拼接视频（{'9:16 竖屏' if vertical_9_16 else '原比例'}）\n\n"
        f"输出：`{out}`（{size_mb:.1f} MB）",
        out,
    )
