"""Pipeline 输入与平台预设单元测试。"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from python_agent.pipeline_input import (
    brief_to_clips,
    load_pipeline_pack,
    parse_script_txt,
    save_video_clips_plan,
)
from python_agent.pipeline_quality import brief_is_renderable
from python_agent.pipeline_render import allocate_broll_timings, trim_to_max_duration
from python_agent.platform_presets import get_platform_preset, is_video_platform


SAMPLE_BRIEF = {
    "content_key": "aisoul:article:1",
    "article_id": 1,
    "title": "Demo",
    "hook": "这是一条足够长的钩子，用于测试口播可渲染判断",
    "talking_points": ["要点一：产品能解决创作者的时间成本问题", "要点二：适合独立开发者快速验证"],
    "cta": "完整拆解见简介链接",
    "tags": ["AI"],
}

SAMPLE_SCRIPT = """【钩子】脚本钩子

1. 脚本要点一
2. 脚本要点二

【引导】脚本引导语
"""


class PipelineInputTests(unittest.TestCase):
    def test_parse_script_txt(self):
        parsed = parse_script_txt(SAMPLE_SCRIPT)
        self.assertEqual(parsed["hook"], "脚本钩子")
        self.assertEqual(len(parsed["talking_points"]), 2)
        self.assertEqual(parsed["cta"], "脚本引导语")

    def test_load_pipeline_pack_prefers_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "brief.json").write_text(
                json.dumps(SAMPLE_BRIEF, ensure_ascii=False),
                encoding="utf-8",
            )
            (root / "script.txt").write_text(SAMPLE_SCRIPT, encoding="utf-8")
            pack = load_pipeline_pack(root)
            self.assertEqual(pack["brief"]["hook"], "脚本钩子")
            self.assertEqual(pack["brief"]["talking_points"][0], "脚本要点一")

    def test_brief_to_clips_douyin(self):
        preset = get_platform_preset("douyin")
        clips = brief_to_clips(SAMPLE_BRIEF, preset)
        self.assertGreaterEqual(len(clips), 3)
        self.assertTrue(all(c.get("tts_text") for c in clips))

    def test_allocate_broll_timings(self):
        clips = [
            {"start": 0, "end": 5, "tts_text": "a"},
            {"start": 0, "end": 5, "tts_text": "b"},
        ]
        tts = [{"duration": 4.0}, {"duration": 6.0}]
        allocate_broll_timings(clips, tts, broll_duration=30.0)
        self.assertLess(clips[0]["start"], clips[1]["start"])
        self.assertAlmostEqual(clips[0]["end"] - clips[0]["start"], 4.0, places=1)

    def test_toutiao_is_article_not_video(self):
        preset = get_platform_preset("toutiao")
        self.assertEqual(preset.content_kind, "article")
        self.assertFalse(is_video_platform("toutiao"))

    def test_resolve_video_platforms_default(self):
        from python_agent.pipeline_input import resolve_video_platforms

        presets = resolve_video_platforms()
        ids = [p.id for p in presets]
        self.assertEqual(ids, ["douyin", "xhs"])

    def test_brief_is_renderable(self):
        ok, _ = brief_is_renderable(SAMPLE_BRIEF)
        self.assertTrue(ok)

    def test_save_video_clips_plan(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            p = save_video_clips_plan(tmp, "douyin", [{"start": 0, "end": 5, "tts_text": "a"}])
            self.assertTrue(p.is_file())

    def test_trim_to_max_duration(self):
        clips = [{"tts_text": "a"}, {"tts_text": "b"}, {"tts_text": "c"}]
        tts = [{"duration": 30}, {"duration": 30}, {"duration": 30}]
        kept_c, kept_t = trim_to_max_duration(clips, tts, max_seconds=50)
        self.assertEqual(len(kept_c), 1)
        self.assertEqual(len(kept_t), 1)


if __name__ == "__main__":
    unittest.main()
