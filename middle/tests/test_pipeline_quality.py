from __future__ import annotations

import unittest

from python_agent.pipeline_quality import (
    brief_for_platform,
    brief_is_renderable,
    truncate_sentence,
)
from python_agent.platform_presets import get_platform_preset


class PipelineQualityTests(unittest.TestCase):
    def test_brief_is_renderable_ok(self):
        ok, _ = brief_is_renderable(
            {
                "hook": "这是一条足够长的钩子文案，用于短视频开场",
                "talking_points": [
                    "要点一：产品能显著节省创作者剪辑与写稿时间",
                    "要点二：适合营销团队批量产出竖屏内容",
                ],
                "cta": "完整变现拆解与链接见简介",
            }
        )
        self.assertTrue(ok)

    def test_brief_is_renderable_short(self):
        ok, reason = brief_is_renderable({"hook": "短", "talking_points": [], "cta": ""})
        self.assertFalse(ok)
        self.assertTrue("钩子" in reason or "实质" in reason)

    def test_brief_for_platform_truncates(self):
        preset = get_platform_preset("douyin")
        brief = {
            "hook": "x" * 80,
            "talking_points": ["a" * 100, "b" * 100, "c" * 100, "d" * 100],
            "cta": "y" * 80,
        }
        out = brief_for_platform(brief, preset)
        self.assertLessEqual(len(out["hook"]), 42)
        self.assertLessEqual(len(out["talking_points"]), 3)

    def test_truncate_sentence(self):
        self.assertTrue(truncate_sentence("hello world", 20).endswith("hello world") or len(truncate_sentence("x" * 30, 10)) <= 10)


if __name__ == "__main__":
    unittest.main()
