"""B-roll 时间轴预分配与封面预取。"""
from __future__ import annotations

from pathlib import Path

from python_agent.pipeline_render import (
    clips_need_broll_retiming,
    estimate_tts_durations_from_clips,
    sync_broll_timings_to_clips,
)


def test_sync_broll_spreads_starts() -> None:
    clips = [
        {"start": 0, "end": 5, "tts_text": "第一句钩子文案稍长一些"},
        {"start": 0, "end": 5, "tts_text": "第二句正文同样要占一定时长"},
    ]
    assert clips_need_broll_retiming(clips)
    est = estimate_tts_durations_from_clips(clips)
    assert len(est) == 2
    assert sync_broll_timings_to_clips(clips, 60.0, tts_clips=est)
    starts = [c["start"] for c in clips]
    assert len(set(round(s, 1) for s in starts)) > 1
    assert all(c["end"] > c["start"] for c in clips)


def test_prefetch_cover_local(tmp_path: Path) -> None:
    from python_agent.pipeline_media import prefetch_task_cover

    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "cover.jpg").write_bytes(b"\xff\xd8\xff" + b"x" * 1200)
    got = prefetch_task_cover(tmp_path, {"cover_image_url": "https://example.com/x.jpg"})
    assert got is not None
    assert got.is_file()
