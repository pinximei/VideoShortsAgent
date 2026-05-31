"""特效审计分级。"""
from __future__ import annotations

from pathlib import Path

from pipeline.effects_audit import audit_task_effects


def test_audit_ok_without_render_effects_if_video_present(tmp_path: Path) -> None:
    task = tmp_path / "889"
    (task / "llm").mkdir(parents=True)
    (task / "videos").mkdir()
    (task / "videos" / "douyin.mp4").write_bytes(b"x" * 60_000)
    (task / "llm" / "video_clips_douyin.json").write_text(
        '{"clips":[{"start":0,"end":5,"hook_text":"a","tts_text":"b","transition_to_next":"fade"}],'
        '"effects":{"preset":"科技"}}',
        encoding="utf-8",
    )
    report = audit_task_effects(task, platforms=["douyin"])
    assert report["ok"] is False
    assert "render_effects_missing" in str(report.get("warnings", []))
