"""平台固定发布脚本基类。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PublishPack:
    article_id: int
    channel_id: str
    title: str = ""
    body: str = ""
    tags: list[str] = field(default_factory=list)
    video_path: Path | None = None
    cover_path: Path | None = None
    output_dir: Path | None = None


@dataclass
class ScriptStepResult:
    step: str
    ok: bool
    detail: str = ""


class PlatformPublishScript(ABC):
    channel_id: str = ""
    creator_url: str = ""
    fixed_steps: tuple[str, ...] = ()

    @abstractmethod
    def run(self, page: Any, pack: PublishPack) -> dict[str, Any]:
        raise NotImplementedError

    def step_log(self, results: list[ScriptStepResult], step: str, ok: bool, detail: str = "") -> None:
        results.append(ScriptStepResult(step=step, ok=ok, detail=detail))
