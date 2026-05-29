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

    douyin_title = f"{brief.hook}｜{brief.title}"[:55]
    _write_text(publish / "douyin_title.txt", douyin_title)
    _write_text(publish / "douyin_tags.txt", " ".join(f"#{t}" for t in brief.tags[:5]))

    xhs_title = f"{brief.hook}\n{brief.title}"[:40]
    _write_text(publish / "xhs_title.txt", xhs_title)
    _write_text(publish / "xhs_body.txt", script_text(brief)[:900])

    toutiao = f"{brief.title}\n\n" + "\n".join(f"· {p}" for p in brief.talking_points) + f"\n\n{brief.cta}"
    _write_text(publish / "toutiao_micro.txt", toutiao[:2000])

    douban = (
        f"《{brief.title}》观察\n\n"
        + "\n".join(brief.talking_points)
        + f"\n\n更多数据与链接：{brief.detail_url}"
    )
    _write_text(publish / "douban_note.txt", douban[:1500])

    _write_text(
        output_dir / "publish_meta.json",
        json.dumps({"source": "template"}, ensure_ascii=False, indent=2),
    )

    return publish
