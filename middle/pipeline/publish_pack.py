from __future__ import annotations

import json
from pathlib import Path

from .models import VideoBrief


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def script_text(brief: VideoBrief) -> str:
    lines = [
        f"【钩子】{brief.hook}",
        "",
    ]
    for i, p in enumerate(brief.talking_points, 1):
        lines.append(f"{i}. {p}")
    lines.extend(["", f"【引导】{brief.cta}"])
    return "\n".join(lines)


def write_publish_pack_templates(brief: VideoBrief, output_dir: Path) -> Path:
    """无 LLM 时的模板回退（仅调试）。"""
    publish = output_dir / "publish"
    publish.mkdir(parents=True, exist_ok=True)

    _write_text(output_dir / "brief.json", json.dumps(brief.to_dict(), ensure_ascii=False, indent=2))
    _write_text(output_dir / "script.txt", script_text(brief))

    _write_text(publish / "douyin_tags.txt", " ".join(f"#{t}" for t in brief.tags[:5]))

    xhs_title = f"{brief.hook}\n{brief.title}"[:40]
    _write_text(publish / "xhs_title.txt", xhs_title)
    _write_text(publish / "xhs_body.txt", script_text(brief)[:900])

    from publisher.scripts.format_copy import format_douban_note, format_douyin_title_desc, format_toutiao_micro

    hook = brief.hook
    toutiao_raw = (
        f"{hook}\n\n{brief.title}\n\n"
        + " ".join(brief.talking_points)
        + f"\n\n{brief.detail_url}"
    )
    _write_text(publish / "toutiao_micro.txt", format_toutiao_micro(hook, toutiao_raw)[:2000])

    douban_raw = f"{hook}\n\n" + "\n".join(brief.talking_points) + f"\n\n{brief.detail_url}"
    _write_text(publish / "douban_note.txt", format_douban_note(hook, douban_raw)[:1500])

    dy_short, dy_desc = format_douyin_title_desc(
        f"{brief.hook}｜{brief.title}"[:55] if brief.title else brief.hook[:55],
        douban_raw,
    )
    _write_text(publish / "douyin_title.txt", dy_short)
    _write_text(publish / "douyin_desc.txt", dy_desc)

    _write_text(
        output_dir / "publish_meta.json",
        json.dumps({"source": "template"}, ensure_ascii=False, indent=2),
    )

    return publish
