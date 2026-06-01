from python_agent.montage_timing import (
    montage_duration_seconds,
    montage_total_frames,
    slide_duration_frames,
)


def test_slide_duration_includes_pad():
    assert slide_duration_frames(2.0, 30) == int(2.3 * 30)


def test_montage_subtracts_transitions():
    frames = [90, 90, 90]
    assert montage_total_frames(frames) == 90 * 3 - 14 * 2
    assert montage_duration_seconds(frames, 30) == montage_total_frames(frames) / 30
