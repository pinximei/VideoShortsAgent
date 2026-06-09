"""抖音 — 发布后验收：作品管理列表含标题。"""
from __future__ import annotations

from typing import Any

from publisher.scripts.common import sleep_ms, wait_manage_list_has_needle, wait_spa_content_ready

from ..pack import VerifyPack
from .base import PlatformVerifyScript, VerifyStepResult
from .common_verify import (
    assert_logged_in_generic,
    check_publish_steps_fallback,
    find_needle_on_page,
    try_evidence_url,
)

MANAGE_URL = "https://creator.douyin.com/creator-micro/content/manage"
SEL_LOGIN = "text=扫码登录"


class DouyinVerifyScript(PlatformVerifyScript):
    channel_id = "douyin"
    script_id = "douyin_verify_v1"
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
            self.step_log(results, "open_manage_or_publish_url", True, ev_url.get("url", ""))
            self.step_log(results, "assert_logged_in", True, "via_publish_url")
            self.step_log(results, "find_title_in_list", True, ev_url.get("detail", ""))
            self.step_log(results, "confirm_item_visible", True)
            return self._out(results, ok=True, evidence=evidence, pack=pack, page=page)

        try:
            page.goto(MANAGE_URL, wait_until="domcontentloaded", timeout=90_000)
            sleep_ms(2000)
            wait_spa_content_ready(page, timeout_ms=90_000)
            self.step_log(results, "open_manage_or_publish_url", True, page.url)
        except Exception as e:
            self.step_log(results, "open_manage_or_publish_url", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        ok_login, detail = assert_logged_in_generic(page, login_markers=("passport", "login"))
        if page.locator(SEL_LOGIN).count() > 0:
            ok_login = False
            detail = "scan_login_visible"
        self.step_log(results, "assert_logged_in", ok_login, detail)
        if not ok_login:
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        ok_list, list_ev = wait_manage_list_has_needle(
            page,
            MANAGE_URL,
            pack.title_needle or pack.title,
            timeout_ms=60_000,
            tab_labels=("已发布", "全部", "审核中", "草稿", ""),
        )
        if ok_list:
            evidence.update(list_ev)
            self.step_log(results, "find_title_in_list", True, list_ev.get("detail", ""))
            self.step_log(results, "confirm_item_visible", True)
            return self._out(results, ok=True, evidence=evidence, pack=pack, page=page)

        found, how = find_needle_on_page(page, pack, scroll_times=5)
        evidence["match_method"] = how
        self.step_log(results, "find_title_in_list", found, how)
        if not found:
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        self.step_log(results, "confirm_item_visible", True, pack.title[:30])
        evidence["manage_url"] = page.url
        return self._out(results, ok=True, evidence=evidence, pack=pack, page=page)
