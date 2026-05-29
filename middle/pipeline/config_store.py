"""读写 config.yaml（保留未改字段）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def read_yaml_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def write_yaml_dict(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def update_config_sections(path: Path, **sections: Any) -> dict[str, Any]:
    raw = read_yaml_dict(path)
    for key, value in sections.items():
        raw[key] = value
    write_yaml_dict(path, raw)
    return raw
