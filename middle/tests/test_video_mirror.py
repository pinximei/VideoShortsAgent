from __future__ import annotations

from pathlib import Path

from pipeline.config import PipelineConfig
from pipeline.video_mirror import apply_video_mirror, render_platform_ids


def test_render_platform_ids_template_only() -> None:
    cfg = PipelineConfig(
        render_platforms=["douyin", "xhs"],
        render_video_template_platform="douyin",
        render_mirror_video_to=["xhs"],
    )
    assert render_platform_ids(cfg) == ["douyin"]


def test_apply_video_mirror_copies_mp4(tmp_path: Path) -> None:
    cfg = PipelineConfig(
        render_video_template_platform="douyin",
        render_mirror_video_to=["xhs"],
    )
    task = tmp_path / "885"
    (task / "videos").mkdir(parents=True)
    src = task / "videos" / "douyin.mp4"
    src.write_bytes(b"\x00" * 80_000)
    written = apply_video_mirror(cfg, task)
    assert written == ["xhs"]
    assert (task / "videos" / "xhs.mp4").is_file()
    assert (task / "videos" / "xhs.mp4").stat().st_size == src.stat().st_size
