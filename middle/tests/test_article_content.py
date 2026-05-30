"""文章实质内容检测。"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.article_content import (
    article_has_substantive_content,
    collect_article_text,
    extract_talking_point_candidates,
    substantive_char_count,
)


def test_link_only_rejected() -> None:
    article = {
        "title": "某工具",
        "summary": "https://example.com/foo",
        "source_original_url": "https://example.com/foo",
        "tabs": [{"label": "描述", "summary": "https://example.com/foo", "body_md": ""}],
    }
    ok, reason = article_has_substantive_content(article)
    assert not ok
    assert "链接" in reason or "过短" in reason


def test_rich_tabs_accepted() -> None:
    article = {
        "title": "DemoApp",
        "tabs": [
            {
                "label": "描述",
                "summary": "面向自媒体的本地视频工具，节省剪辑时间。",
                "body_md": "支持一键生成字幕与多平台导出。",
            },
            {"label": "变现评估", "summary": "订阅 9.9 美元/月，企业按项目收费。"},
        ],
        "replication_analysis": {"worth_score": 8, "value_summary": "创作者愿为省时间付费"},
    }
    ok, _ = article_has_substantive_content(article)
    assert ok
    points = extract_talking_point_candidates(article)
    assert len(points) >= 2
    assert substantive_char_count(collect_article_text(article)) >= 60


def test_article_body_included_in_collect() -> None:
    article = {
        "title": "快讯",
        "article_body": (
            "OpenAI 发布新模型，支持更长上下文窗口，面向企业 API 客户。"
            "业内认为这将改变长文档问答与代码辅助场景，开发者可更低成本接入。"
        ),
        "summary": "https://example.com/x",
    }
    blob = collect_article_text(article)
    assert "OpenAI" in blob
    ok, _ = article_has_substantive_content(article)
    assert ok


def test_fixture_article_has_content() -> None:
    p = Path(__file__).parent / "fixtures" / "article_detail.json"
    article = json.loads(p.read_text(encoding="utf-8"))
    ok, _ = article_has_substantive_content(article)
    assert ok
