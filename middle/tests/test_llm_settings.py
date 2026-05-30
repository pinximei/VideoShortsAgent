from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.llm_settings import mask_api_key, read_env_dict, write_env_updates


class LlmSettingsTests(unittest.TestCase):
    def test_mask_api_key(self):
        self.assertEqual(mask_api_key(""), "")
        self.assertIn("...", mask_api_key("sk-abcdefghijklmnop"))

    def test_write_env_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("FOO=bar\n", encoding="utf-8")
            with patch("pipeline.llm_settings.env_file_path", return_value=env):
                write_env_updates({"DEEPSEEK_API_KEY": "sk-test", "LLM_MODEL": "deepseek-chat"})
            data = read_env_dict(env)
            self.assertEqual(data["DEEPSEEK_API_KEY"], "sk-test")
            self.assertEqual(data["LLM_MODEL"], "deepseek-chat")
            self.assertEqual(data["FOO"], "bar")


if __name__ == "__main__":
    unittest.main()
