"""封面资源解析。"""
from __future__ import annotations

from pathlib import Path

from python_agent.pipeline_media import apply_intro_cover_from_brief, remotion_public_image


def test_apply_intro_cover_local(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    cover = assets / "cover.jpg"
    cover.write_bytes(b"\xff\xd8\xff" + b"x" * 1200)
    fx = apply_intro_cover_from_brief(
        {"intro_card": True},
        tmp_path,
        {"title": "Demo Title", "article_id": 1},
    )
    assert fx.get("intro_subheading") == "Demo Title"
    assert fx.get("intro_image_path")
    assert fx.get("intro_card") is True
    rem = remotion_public_image(cover, task_tag="t1")
    assert rem and rem.startswith("/images/")
