"""强制 LLM 润色门禁。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.config import PipelineConfig
from pipeline.llm_polish import assert_llm_polished
from pipeline.pipeline_gates import PipelineGateError
from pipeline.platform_llm import write_publish_pack
from pipeline.models import VideoBrief


BRIEF = VideoBrief(
    content_key="aisoul:article:9",
    article_id=9,
    title="Soul 原标题",
    hook="Soul 钩子",
    talking_points=["Soul 要点"],
    cta="见链接",
    tags=["AI"],
    feed_kind="news",
)


def _valid_copy() -> dict:
    long_tts = "LLM润色后的口播内容需要足够长才能通过校验规则与门禁检查要求"
    return {
        "douyin": {
            "title": "LLM 抖音标题",
            "tags": ["AI"],
            "script": long_tts,
            "effects": {"preset": "活力"},
            "clips": [
                {
                    "start": 0,
                    "end": 8,
                    "hook_text": "钩子",
                    "tts_text": long_tts,
                    "caption_style": "spring",
                    "transition_to_next": "fade",
                },
                {
                    "start": 12,
                    "end": 20,
                    "hook_text": "正文",
                    "tts_text": long_tts + "第二段",
                    "caption_style": "spring",
                    "transition_to_next": "fade",
                },
            ],
        },
        "xhs": {"title": "LLM 小红书", "body": "LLM 笔记正文", "video_script": long_tts},
        "toutiao": {"title": "LLM 头条", "body": "LLM 微头条润色正文"},
        "douban": {"title": "LLM 豆瓣", "body": "LLM 豆瓣润色笔记"},
    }


def test_assert_llm_polished_ok(tmp_path: Path) -> None:
    out = tmp_path / "task"
    out.mkdir()
    (out / "llm").mkdir()
    (out / "llm" / "platform_copy.json").write_text(
        json.dumps(_valid_copy(), ensure_ascii=False), encoding="utf-8"
    )
    (out / "publish_meta.json").write_text(
        json.dumps({"source": "pipeline_llm"}), encoding="utf-8"
    )
    cfg = PipelineConfig(llm_enabled=True, llm_require_polish=True)
    assert_llm_polished(out, cfg)


def test_assert_llm_polished_rejects_template(tmp_path: Path) -> None:
    out = tmp_path / "task"
    out.mkdir()
    (out / "publish_meta.json").write_text(
        json.dumps({"source": "template"}), encoding="utf-8"
    )
    cfg = PipelineConfig(llm_enabled=True, llm_require_polish=True)
    with pytest.raises(PipelineGateError, match="llm_polish_required"):
        assert_llm_polished(out, cfg)


def test_write_publish_pack_rejects_without_llm(tmp_path: Path) -> None:
    cfg = PipelineConfig(
        llm_enabled=True,
        llm_require_polish=True,
        render_allow_template_fallback=False,
        pipeline_fail_closed=True,
    )
    out = tmp_path / "task"
    with pytest.raises((PipelineGateError, RuntimeError, ValueError)):
        write_publish_pack(BRIEF, out, cfg=cfg, platform_copy={})
