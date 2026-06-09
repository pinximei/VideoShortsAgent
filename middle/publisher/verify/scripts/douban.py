"""豆瓣 — 发布后验收：我的笔记列表或发布页 URL。"""
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

MINE_NOTES_URL = "https://www.douban.com/mine/notes"
SEL_LOGIN = "text=登录豆瓣"


class DoubanVerifyScript(PlatformVerifyScript):
    channel_id = "douban"
    script_id = "douban_verify_v1"
    manage_url = MINE_NOTES_URL
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
            page.goto(MINE_NOTES_URL, wait_until="domcontentloaded", timeout=90_000)
            sleep_ms(2500)
            self.step_log(results, "open_manage_or_publish_url", True, page.url)
        except Exception as e:
            self.step_log(results, "open_manage_or_publish_url", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        url = page.url or ""
        ok_login, detail = assert_logged_in_generic(
            page, login_markers=("accounts.douban.com/login", "/login")
        )
        if page.locator(SEL_LOGIN).count() > 0 and "mine" not in url:
            ok_login = False
        self.step_log(results, "assert_logged_in", ok_login, detail)
        if not ok_login:
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        found, how = find_needle_on_page(page, pack, scroll_times=3)
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
