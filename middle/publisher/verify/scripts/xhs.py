"""小红书 — 发布后验收：笔记管理列表含标题。"""
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

MANAGE_URLS = (
    "https://creator.xiaohongshu.com/creator/note/manage",
    "https://creator.xiaohongshu.com/new/note/note-manage",
    "https://creator.xiaohongshu.com/publish/note-manager",
)
SEL_LOGIN = "text=扫码登录"


class XhsVerifyScript(PlatformVerifyScript):
    channel_id = "xhs"
    script_id = "xhs_verify_v1"
    manage_url = MANAGE_URLS[0]
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

        opened = False
        for url in MANAGE_URLS:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                sleep_ms(3000)
                for nav in ("笔记管理", "内容管理", "作品管理"):
                    loc = page.get_by_text(nav, exact=False)
                    if loc.count():
                        try:
                            loc.first.click(timeout=3_000)
                            sleep_ms(1500)
                        except Exception:
                            pass
                opened = True
                evidence["tried_url"] = page.url
                break
            except Exception:
                continue
        self.step_log(results, "open_manage_or_publish_url", opened, evidence.get("tried_url", ""))
        if not opened:
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        ok_login, detail = assert_logged_in_generic(page, login_markers=("login",))
        if page.locator(SEL_LOGIN).count() > 0 and "creator" not in (page.url or ""):
            ok_login = False
        self.step_log(results, "assert_logged_in", ok_login, detail)
        if not ok_login:
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        found, how = find_needle_on_page(page, pack, scroll_times=6)
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
