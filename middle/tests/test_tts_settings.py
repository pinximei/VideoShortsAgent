"""TTS / DashScope 设置读写。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.llm_settings import read_env_dict
from pipeline.tts_settings import (
    dashscope_api_key,
    save_tts_settings,
    tts_settings_public,
)


class TtsSettingsTests(unittest.TestCase):
    def test_save_dashscope_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            with patch("pipeline.llm_settings.env_file_path", return_value=env):
                with patch("pipeline.tts_settings.env_file_path", return_value=env):
                    save_tts_settings(dashscope_api_key="sk-dash-test")
            data = read_env_dict(env)
            self.assertEqual(data["DASHSCOPE_API_KEY"], "sk-dash-test")

    def test_public_masked(self):
        with patch.dict("os.environ", {"DASHSCOPE_API_KEY": "sk-abcdefghijklmnop"}, clear=False):
            pub = tts_settings_public()
            self.assertTrue(pub["dashscope_api_key_set"])
            self.assertIn("...", pub["dashscope_api_key_masked"])
            self.assertEqual(dashscope_api_key(), "sk-abcdefghijklmnop")


if __name__ == "__main__":
    unittest.main()
