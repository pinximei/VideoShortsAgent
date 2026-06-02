import json

from python_agent.eval_mock_compose import mock_compose_from_brief
from python_agent.platform_caption_presets import reconcile_platform_slides
from python_agent.slides_quality_gates import auto_fix_slides
from scripts.douyin_layout_audit import run_audit


def test_douyin_mock_passes_layout_audit(tmp_path) -> None:
    brief = {"platform": "douyin", "feed_kind": "github_daily", "stars": "12k"}
    script = mock_compose_from_brief(brief)
    slides = auto_fix_slides(
        reconcile_platform_slides(script["slides"], "douyin"),
        platform="douyin",
        brief=brief,
    )
    task = tmp_path / "task"
    llm = task / "llm"
    llm.mkdir(parents=True)

    (llm / "slides_script.json").write_text(
        json.dumps({"slides": slides}, ensure_ascii=False),
        encoding="utf-8",
    )
    result = run_audit(task)
    assert result["ok"], result["issues"]
    assert result["pass_count"] == 4
