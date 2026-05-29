from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from pipeline.config import PipelineConfig
from pipeline.db import JobStore
from pipeline.orchestrator import run_pipeline


def _article() -> dict:
    p = Path(__file__).parent / "fixtures" / "article_detail.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_run_pipeline_mock_soul(tmp_path: Path) -> None:
    cfg = PipelineConfig(
        data_dir=tmp_path,
        min_worth_score=7,
        feed_kinds=["apps"],
        public_base_url="https://ai-trends.news",
        render_enabled=False,
        llm_enabled=False,
    )
    soul = MagicMock()
    soul.list_feed.return_value = [
        {
            "id": 870,
            "title": "Demo",
            "feed_kind": "apps",
            "replication_analysis": {"worth_score": 8},
        }
    ]
    soul.get_article.return_value = _article()

    stats = run_pipeline(cfg, soul=soul)
    assert stats.discovered == 1
    assert stats.packed == 1
    assert stats.deduped == 0

    out = tmp_path / "output" / "870" / "script.txt"
    assert out.is_file()

    stats2 = run_pipeline(cfg, soul=soul)
    assert stats2.deduped == 1
    assert stats2.packed == 0
