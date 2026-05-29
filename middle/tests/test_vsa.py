"""VSA 执行层测试。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.config import PipelineConfig
from pipeline.task_pack import load_video_clips


class VsaTests(unittest.TestCase):
    def test_load_video_clips_missing_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                load_video_clips(Path(tmp), "douyin")

    def test_load_video_clips_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            llm = root / "llm"
            llm.mkdir()
            (llm / "video_clips_douyin.json").write_text(
                json.dumps({"clips": [{"start": 0, "end": 5, "tts_text": "hi"}]}),
                encoding="utf-8",
            )
            clips = load_video_clips(root, "douyin")
            self.assertEqual(len(clips), 1)


if __name__ == "__main__":
    unittest.main()
