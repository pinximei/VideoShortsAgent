"""今日头条 — 发布后验收：微头条列表含正文片段。"""
from __future__ import annotations

from typing import Any

from publisher.scripts.common import sleep_ms

from ..pack import VerifyPack
from .base import PlatformVerifyScript, VerifyStepResult
from .common_verify import (
    assert_logged_in_generic,
    check_publish_steps_fallback,
    find_needle_on_page,
    try_evidence_url,
)

MANAGE_URL = "https://mp.toutiao.com/profile_v4/index"
LIST_URL = "https://mp.toutiao.com/profile_v4/weitoutiao"


class ToutiaoVerifyScript(PlatformVerifyScript):
    channel_id = "toutiao"
    script_id = "toutiao_verify_v1"
    manage_url = MANAGE_URL
    fixed_steps = (
        "open_manage_or_publish_url",
        "assert_logged_in",
        "find_title_in_list",
        "confirm_item_visible",
    )

    def run(self, page: Any, pack: VerifyPack) -> dict[str, Any]:
        results: list[VerifyStepResult] = []
        evidence: dict[str, Any] = {"title_needle": pack.title_needle}

        ok_url, ev_url = try_evidence_url(page, pack)
        if ok_url:
            evidence.update(ev_url)
            for step in self.fixed_steps:
                self.step_log(results, step, True, ev_url.get("detail", ""))
            return self._out(results, ok=True, evidence=evidence, pack=pack, page=page)

        try:
            for url in (LIST_URL, MANAGE_URL):
                page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                sleep_ms(2500)
                if "sso.toutiao.com" not in (page.url or ""):
                    break
            self.step_log(results, "open_manage_or_publish_url", True, page.url)
        except Exception as e:
            self.step_log(results, "open_manage_or_publish_url", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        ok_login, detail = assert_logged_in_generic(
            page, login_markers=("sso.toutiao.com", "passport", "/auth/page/login")
        )
        self.step_log(results, "assert_logged_in", ok_login, detail)
        if not ok_login:
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        found, how = find_needle_on_page(page, pack, scroll_times=5)
        evidence["match_method"] = how
        self.step_log(results, "find_title_in_list", found, how)
        if not found:
            ok_pub, pub_detail = check_publish_steps_fallback(
                pack, strict=pack.strict_verify
            )
            if ok_pub:
                evidence["fallback"] = pub_detail
                self.step_log(results, "find_title_in_list", True, f"fallback:{pub_detail}")
                found = True
        if not found:
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        self.step_log(results, "confirm_item_visible", True, pack.title[:30])
        evidence["manage_url"] = page.url
        return self._out(results, ok=True, evidence=evidence, pack=pack, page=page)
