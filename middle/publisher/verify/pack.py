"""发布后验收 — 期望标题/正文片段（从任务目录读取）。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pipeline.config import PipelineConfig
from pipeline.platform_presets import get_platform_preset, is_video_platform


@dataclass
class VerifyPack:
    article_id: int
    channel_id: str
    title: str
    body_snippet: str
    title_needle: str
    output_dir: Path
    publish_evidence: dict
    strict_verify: bool = True


def normalize_needle(text: str, *, max_len: int = 18, min_len: int = 4) -> str:
    t = re.sub(r"\s+", "", (text or "").strip())
    if len(t) < min_len:
        return t
    return t[:max_len]


def load_verify_pack(cfg: PipelineConfig, article_id: int, channel_id: str) -> VerifyPack:
    out_dir = cfg.output_root / str(article_id)
    publish_dir = out_dir / "publish"
    preset = get_platform_preset(channel_id)

    title = ""
    body = ""
    if is_video_platform(channel_id):
        tp = publish_dir / f"{channel_id}_title.txt"
        bp = publish_dir / f"{channel_id}_body.txt"
        if tp.is_file():
            title = tp.read_text(encoding="utf-8").strip()
        if bp.is_file():
            body = bp.read_text(encoding="utf-8").strip()[:200]
    else:
        ap = publish_dir / preset.publish_file
        if ap.is_file():
            raw = ap.read_text(encoding="utf-8").strip()
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            if lines:
                title = lines[0]
                body = "\n".join(lines[1:])[:200] if len(lines) > 1 else raw[:200]
        tp = publish_dir / f"{channel_id}_title.txt"
        if tp.is_file():
            title = tp.read_text(encoding="utf-8").strip() or title

    evidence: dict = {}
    steps_path = publish_dir / f"{channel_id}_publish_steps.json"
    if steps_path.is_file():
        try:
            steps_doc = json.loads(steps_path.read_text(encoding="utf-8"))
            if isinstance(steps_doc, dict):
                evidence = dict(steps_doc.get("evidence") or {})
        except Exception:
            pass

    needle = normalize_needle(title) or normalize_needle(body[:40])
    if not needle:
        raise ValueError(f"无法生成标题匹配针 article={article_id} channel={channel_id}")

    return VerifyPack(
        article_id=article_id,
        channel_id=channel_id,
        title=title,
        body_snippet=body[:200],
        title_needle=needle,
        output_dir=out_dir,
        publish_evidence=evidence,
        strict_verify=bool(getattr(cfg.publisher, "strict_publish", True)),
    )
