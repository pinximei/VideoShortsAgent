"""全片 Star 数 / stat 展示与 brief 单一来源对齐。"""
from __future__ import annotations

import re
from typing import Any

from python_agent.douyin_shot_stylist import format_stars_display, parse_star_count


def expected_star_from_brief(brief: dict[str, Any] | None) -> tuple[int, str]:
    b = brief or {}
    raw = b.get("stars") or b.get("star_count") or ""
    n = parse_star_count(raw)
    label = format_stars_display(n) if n else str(raw).strip()[:12]
    return n, label


def _norm_stat(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip().lower())


def validate_stars_consistency(
    slides: list[dict[str, Any]],
    brief: dict[str, Any] | None = None,
) -> list[str]:
    """返回错误列表；brief 无 star 时跳过。"""
    star_n, label = expected_star_from_brief(brief)
    if not star_n:
        return []
    errors: list[str] = []
    label_n = _norm_stat(label)
    for i, s in enumerate(slides):
        sc = int(s.get("star_count") or 0)
        if sc and sc != star_n:
            errors.append(f"slide_{i}_star_count_mismatch:{sc}!={star_n}")
        sv = str(s.get("stat_value") or "").strip()
        if sv and _norm_stat(sv) != label_n and _norm_stat(sv) != _norm_stat(str(star_n)):
            errors.append(f"slide_{i}_stat_value_mismatch:{sv}!={label}")
        stars_field = str(s.get("stars") or "").strip()
        sf = _norm_stat(stars_field)
        if stars_field and label_n not in sf and sf != label_n:
            errors.append(f"slide_{i}_stars_field_mismatch:{stars_field}!={label}")
    return errors


def audit_star_labels(slides: list[dict[str, Any]], brief: dict[str, Any] | None = None) -> dict[str, Any]:
    star_n, label = expected_star_from_brief(brief)
    seen: set[str] = set()
    for s in slides:
        for key in ("stat_value", "stars"):
            v = str(s.get(key) or "").strip()
            if v:
                seen.add(v)
        sc = int(s.get("star_count") or 0)
        if sc:
            seen.add(format_stars_display(sc))
    return {
        "expected_count": star_n,
        "expected_label": label,
        "seen_labels": sorted(seen),
        "ok": not star_n or (len(seen) <= 1 and (not seen or label in seen or format_stars_display(star_n) in seen)),
    }
