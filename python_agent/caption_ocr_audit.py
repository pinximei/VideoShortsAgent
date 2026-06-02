"""底栏字幕 OCR 抽检（可选 tesseract；未安装则跳过）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _ocr_image(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""
    try:
        img = Image.open(path)
        w, h = img.size
        crop = img.crop((0, int(h * 0.72), w, h))
        return (pytesseract.image_to_string(crop, lang="chi_sim+eng") or "").strip()
    except Exception:
        return ""


def audit_frames_ocr(task_dir: Path, *, platform: str = "douyin") -> dict[str, Any]:
    manifest_path = task_dir / "QUALITY_FRAMES.json"
    if not manifest_path.is_file():
        return {"ok": True, "skipped": True, "reason": "no_frames"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    texts: list[dict[str, str]] = []
    for fp in manifest.get("frames") or []:
        p = Path(fp)
        if not p.is_file():
            continue
        text = _ocr_image(p)
        if text:
            texts.append({"frame": p.name, "text": text[:120]})
    if not texts:
        return {"ok": True, "skipped": True, "reason": "pytesseract_unavailable_or_empty"}
    long_lines = [t for t in texts if len(t.get("text") or "") > 40]
    issues = []
    if len(long_lines) >= 3:
        issues.append("caption_band_dense_text")
    return {
        "ok": not issues,
        "samples": texts[:5],
        "issues": issues,
    }
