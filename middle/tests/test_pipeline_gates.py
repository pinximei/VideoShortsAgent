"""pipeline_gates fail-closed 门禁。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.config import PipelineConfig
from unittest.mock import patch
from pipeline.pipeline_gates import (
    PipelineGateError,
    assert_channel_publishable,
    assert_task_ready_for_publish,
    gate_summary,
)


def _minimal_ready_task(cfg: PipelineConfig, *, with_video: bool = True) -> Path:
    task = cfg.output_root / "100"
    (task / "llm").mkdir(parents=True)
    (task / "videos").mkdir(parents=True)
    (task / "publish").mkdir(parents=True)
    bindings = {
        "theme_id": "ai_monetize",
        "channels": {"douyin": {"label": "抖音"}},
    }
    (task / "brief.json").write_text(
        json.dumps(
            {
                "publish_bindings": bindings,
                "feed_kind": "github_daily",
                "hook": "别划走，今天这个开源项目真的炸裂",
                "talking_points": ["第一点", "第二点", "第三点"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (task / "publish_meta.json").write_text(
        json.dumps({"source": "pipeline_llm"}, ensure_ascii=False),
        encoding="utf-8",
    )
    for pid in ("douyin", "xhs"):
        (task / "llm" / f"video_clips_{pid}.json").write_text(
            json.dumps(
                {
                    "clips": [
                        {"start": 0, "end": 5, "tts_text": "hello one"},
                        {"start": 5, "end": 10, "tts_text": "hello two"},
                        {"start": 10, "end": 15, "tts_text": "hello three"},
                    ],
                    "tts_durations": [4.5],
                    "source": "pipeline_llm",
                    "render_status": "ok",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (task / "llm" / f"render_effects_{pid}.json").write_text(
            json.dumps({"applied_effects": {"preset": "科技"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        if with_video:
            (task / "videos" / f"{pid}.mp4").write_bytes(b"x" * 60_000)
    verify = {
        "ok": True,
        "quick": {"ok": True, "platforms": {"douyin": {"ok": True}, "xhs": {"ok": True}}},
        "effects_audit": {"ok": True},
    }
    (task / "verify_report.json").write_text(json.dumps(verify), encoding="utf-8")
    return task


def test_gate_blocks_llm_fallback(tmp_path: Path) -> None:
    cfg = PipelineConfig(
        data_dir=tmp_path,
        render_enabled=True,
        pipeline_fail_closed=True,
        broll_template=str(tmp_path / "broll.mp4"),
    )
    (tmp_path / "broll.mp4").write_bytes(b"fake")
    task = _minimal_ready_task(cfg, with_video=False)
    (task / "publish_meta.json").write_text('{"source":"template"}', encoding="utf-8")
    with pytest.raises(PipelineGateError) as exc:
        assert_task_ready_for_publish(cfg, task)
    assert exc.value.code == "llm_fallback_forbidden"


def test_gate_blocks_bindings_warning(tmp_path: Path) -> None:
    cfg = PipelineConfig(
        data_dir=tmp_path,
        render_enabled=True,
        pipeline_fail_closed=True,
        broll_template=str(tmp_path / "broll.mp4"),
    )
    (tmp_path / "broll.mp4").write_bytes(b"fake")
    task = _minimal_ready_task(cfg)
    brief = {"publish_bindings": {"warning": "no account", "channels": {}}}
    with pytest.raises(PipelineGateError) as exc:
        assert_task_ready_for_publish(cfg, task, brief_dict=brief)
    assert exc.value.code in ("bindings_warning", "bindings_empty")


def test_gate_blocks_verify_failed(tmp_path: Path) -> None:
    cfg = PipelineConfig(
        data_dir=tmp_path,
        render_enabled=True,
        pipeline_fail_closed=True,
        broll_template=str(tmp_path / "broll.mp4"),
    )
    (tmp_path / "broll.mp4").write_bytes(b"fake")
    task = _minimal_ready_task(cfg)
    (task / "verify_report.json").write_text('{"ok":false,"quick":{"ok":true}}', encoding="utf-8")
    with pytest.raises(PipelineGateError) as exc:
        from pipeline.pipeline_gates import assert_verify_report

        assert_verify_report(task, cfg, strict=True)
    assert exc.value.code == "verify_failed"


def test_gate_summary_ok(tmp_path: Path) -> None:
    cfg = PipelineConfig(
        data_dir=tmp_path,
        render_enabled=True,
        pipeline_fail_closed=True,
        broll_template=str(tmp_path / "broll.mp4"),
    )
    (tmp_path / "broll.mp4").write_bytes(b"fake")
    task = _minimal_ready_task(cfg)
    quick_ok = {"ok": True, "platforms": {"douyin": {"ok": True}, "xhs": {"ok": True}}}
    with patch("pipeline.render_verify._quick_video_checks", return_value=quick_ok):
        summary = gate_summary(task, cfg)
    assert summary["ok"] is True


def test_channel_publishable_requires_ready_job(tmp_path: Path) -> None:
    cfg = PipelineConfig(
        data_dir=tmp_path,
        render_enabled=True,
        pipeline_fail_closed=True,
        broll_template=str(tmp_path / "broll.mp4"),
    )
    (tmp_path / "broll.mp4").write_bytes(b"fake")
    task = _minimal_ready_task(cfg)
    job = {"status": "processing", "brief_json": json.loads((task / "brief.json").read_text())}
    with pytest.raises(PipelineGateError) as exc:
        assert_channel_publishable(cfg, 100, "douyin", job=job)
    assert exc.value.code == "job_not_ready"
