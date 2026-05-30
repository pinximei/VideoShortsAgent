"""platform_llm 单元测试（mock LLM）。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pipeline.config import PipelineConfig
from pipeline.models import VideoBrief
from pipeline.platform_llm import write_publish_pack


BRIEF = VideoBrief(
    content_key="aisoul:article:1",
    article_id=1,
    title="测试标题",
    hook="测试钩子",
    talking_points=["要点A", "要点B"],
    cta="见链接",
    tags=["AI"],
)

MOCK_COPY = {
    "douyin": {
        "title": "LLM抖音标题",
        "tags": ["AI工具"],
        "script": "LLM口播稿内容",
        "effects": {"preset": "活力", "gradient": False},
        "clips": [
            {"start": 0, "end": 8, "hook_text": "钩子", "tts_text": "LLM口播第一段内容需要足够长才能通过校验规则", "caption_style": "spring", "transition_to_next": "fade"},
            {"start": 12, "end": 20, "hook_text": "正文", "tts_text": "LLM口播第二段同样要写够字数以满足平台校验", "caption_style": "spring", "transition_to_next": "fade"},
        ],
    },
    "xhs": {
        "title": "LLM小红书",
        "body": "LLM笔记正文",
        "video_script": "LLM小红书口播",
        "effects": {"preset": "情感", "gradient": False},
        "clips": [
            {"start": 0, "end": 8, "hook_text": "分享", "tts_text": "LLM口播第一段内容需要足够长才能通过校验规则", "caption_style": "fade", "transition_to_next": "dissolve"},
            {"start": 14, "end": 22, "hook_text": "要点", "tts_text": "LLM口播第二段同样要写够字数以满足平台校验", "caption_style": "fade", "transition_to_next": "fade"},
        ],
    },
    "toutiao": {"title": "LLM头条", "body": "LLM微头条正文"},
    "douban": {"title": "LLM豆瓣", "body": "LLM豆瓣笔记"},
}


class PlatformLLMTests(unittest.TestCase):
    @patch("pipeline.platform_llm.PipelineLLM")
    def test_write_publish_pack_uses_llm(self, mock_llm_cls: MagicMock):
        mock_llm_cls.return_value.chat_json.return_value = MOCK_COPY
        cfg = PipelineConfig(llm_enabled=True)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_publish_pack(BRIEF, out, cfg=cfg)
            self.assertTrue((out / "publish" / "douyin_title.txt").is_file())
            self.assertIn("LLM抖音标题", (out / "publish" / "douyin_title.txt").read_text(encoding="utf-8"))
            meta = json.loads((out / "publish_meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["source"], "pipeline_llm")
            self.assertTrue((out / "llm" / "video_clips_douyin.json").is_file())


if __name__ == "__main__":
    unittest.main()
