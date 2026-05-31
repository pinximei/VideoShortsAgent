"""DashScope ASR 输出解析与 .env 加载。"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_env() -> None:
    env = ROOT / ".env"
    if not env.is_file():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def extract_text(output) -> tuple[str, list[dict]]:
    if not output:
        return "", []
    if isinstance(output, str):
        return output.strip(), []
    if not isinstance(output, dict):
        return str(output).strip(), []

    sentences = output.get("sentence")
    if sentences is None and isinstance(output.get("sentences"), list):
        sentences = output["sentences"]
    rows: list[dict] = []
    if isinstance(sentences, dict):
        sentences = [sentences]
    if isinstance(sentences, list):
        for s in sentences:
            if not isinstance(s, dict):
                continue
            t = str(s.get("text", "") or "").strip()
            if not t:
                continue
            rows.append(
                {
                    "text": t,
                    "begin_ms": s.get("begin_time"),
                    "end_ms": s.get("end_time"),
                    "chars": len(t.replace(" ", "")),
                }
            )
    if rows:
        return "".join(r["text"] for r in rows), rows

    flat = str(output.get("text", "") or "").strip()
    return flat, [{"text": flat, "chars": len(flat.replace(" ", ""))}] if flat else []
