"""发布后固定验收脚本基类。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..pack import VerifyPack


@dataclass
class VerifyStepResult:
    step: str
    ok: bool
    detail: str = ""


class PlatformVerifyScript(ABC):
    channel_id: str = ""
    manage_url: str = ""
    fixed_steps: tuple[str, ...] = ()

    @abstractmethod
    def run(self, page: Any, pack: VerifyPack) -> dict[str, Any]:
        raise NotImplementedError

    def step_log(self, results: list[VerifyStepResult], step: str, ok: bool, detail: str = "") -> None:
        results.append(VerifyStepResult(step=step, ok=ok, detail=detail))

    def _out(
        self,
        results: list[VerifyStepResult],
        *,
        ok: bool,
        evidence: dict[str, Any],
        pack: VerifyPack | None = None,
        page: Any | None = None,
    ) -> dict[str, Any]:
        if not ok and page is not None and pack is not None:
            from publisher.scripts.common import screenshot_on_fail

            class _P:
                output_dir = pack.output_dir

            screenshot_on_fail(page, _P(), f"{pack.channel_id}_verify_last.png")
        return {
            "channel_id": self.channel_id,
            "ok": ok,
            "verified": ok,
            "evidence": evidence,
            "steps": [r.__dict__ for r in results],
            "script": getattr(self, "script_id", "verify"),
            "title_needle": pack.title_needle if pack else "",
        }
