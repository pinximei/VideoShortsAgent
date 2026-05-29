"""
VSA 执行层：根据中间层 LLM 分镜 JSON 裁剪（保留全部特效能力）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from python_agent.capabilities.registry import merge_render_effects, platform_video_defaults
from python_agent.skills.dubbing_skill import DubbingSkill
from python_agent.skills.render_skill import RenderSkill


def _trim_clips(clips: list[dict], tts_clips: list[dict], max_seconds: float):
    kept_c, kept_t, total = [], [], 0.0
    for c, t in zip(clips, tts_clips):
        dur = float(t.get("duration") or 0)
        if dur <= 0 or total + dur > max_seconds + 0.25:
            break
        kept_c.append(c)
        kept_t.append(t)
        total += dur
    return kept_c or clips[:1], kept_t or tts_clips[:1]


def _format_video(src: str, dst: str, width: int, height: int, platform: str) -> None:
    import os
    import subprocess

    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    if platform == "xhs":
        vf += ",eq=brightness=0.03:saturation=1.08"
    cmd = [
        "ffmpeg", "-y", "-i", src, "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-movflags", "+faststart", "-preset", "fast", dst,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not os.path.isfile(dst):
        raise RuntimeError(f"格式化失败: {(r.stderr or '')[-300:]}")


def render_from_plan(
    *,
    clips: list[dict[str, Any]],
    broll_path: str,
    output_path: str,
    platform: str = "douyin",
    voice: str | None = None,
    max_seconds: float | None = None,
    width: int | None = None,
    height: int | None = None,
    skip_tts: bool = False,
    work_dir: str | None = None,
    effects: dict[str, Any] | None = None,
    use_remotion: bool = False,
) -> dict[str, Any]:
    import os

    if not clips:
        raise ValueError("clips 为空")
    if not os.path.isfile(broll_path):
        raise FileNotFoundError(f"B-roll 不存在: {broll_path}")

    defaults = platform_video_defaults(platform)
    voice = voice or defaults["voice"]
    max_seconds = max_seconds if max_seconds is not None else defaults["max_seconds"]
    width = width or defaults["width"]
    height = height or defaults["height"]

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(work_dir or out.parent / "_vsa_work" / platform)
    tmp.mkdir(parents=True, exist_ok=True)

    render_effects = merge_render_effects(platform, clips, effects, use_remotion=use_remotion)
    analysis = {"clips": clips}
    tts_info: dict[str, Any] = {"tts_clips": []}

    if not skip_tts:
        dubber = DubbingSkill(voice=voice)
        tts_info = dubber.execute(analysis, str(tmp), voice=voice)
        clips, tts_list = _trim_clips(clips, tts_info.get("tts_clips") or [], max_seconds)
        analysis["clips"] = clips
        tts_info["tts_clips"] = tts_list

    renderer = RenderSkill()
    raw = renderer.execute(
        broll_path,
        analysis,
        str(tmp),
        effects=render_effects,
        tts_info=tts_info if tts_info.get("tts_clips") else None,
    )
    if not raw or not os.path.isfile(raw):
        raise RuntimeError("RenderSkill 未产出文件")

    _format_video(raw, str(out), width, height, platform)
    return {
        "ok": True,
        "path": str(out.resolve()),
        "platform": platform,
        "effects_applied": render_effects,
    }


def render_from_plan_file(plan_path: str, broll_path: str, output_path: str, **kwargs: Any) -> dict[str, Any]:
    data = json.loads(Path(plan_path).read_text(encoding="utf-8-sig"))
    clips = data.get("clips") or []
    effects = data.get("effects")
    platform = kwargs.pop("platform", None) or data.get("platform") or "douyin"
    return render_from_plan(
        clips=clips,
        broll_path=broll_path,
        output_path=output_path,
        platform=platform,
        effects=effects,
        **kwargs,
    )
