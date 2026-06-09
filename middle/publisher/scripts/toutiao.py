"""今日头条创作者 — 微头条固定步骤脚本（非 LLM）。"""
from __future__ import annotations

import time
from typing import Any

from .base import PlatformPublishScript, PublishPack, ScriptStepResult
from .common import (
    click_confirm_dialogs,
    page_contains_needle,
    screenshot_on_fail,
    sleep_ms,
    split_title_body,
    wait_for_toast_ok,
    wait_manage_list_has_needle,
)
from .common import fill_editor_content
from .format_copy import format_toutiao_micro, format_toutiao_micro_html

CREATOR_PUBLISH_URL = "https://mp.toutiao.com/profile_v4/weitoutiao/publish"
LIST_URL = "https://mp.toutiao.com/profile_v4/weitoutiao"
SEL_EDITOR = (
    '.editor-kit-container [contenteditable="true"], '
    'div.public-DraftEditor-content[contenteditable="true"], '
    '[data-slate-editor="true"], [class*="editor"] [contenteditable], '
    '.publish-editor [contenteditable="true"], '
    '[contenteditable="true"], textarea, [role="textbox"]'
)
BODY_MAX = 2000
EDITOR_WAIT_MS = 90_000


def normalize_needle_from_title(title: str) -> str:
    t = (title or "").strip().replace(" ", "")
    return t[:18] if len(t) >= 6 else t


class ToutiaoPublishScript(PlatformPublishScript):
    channel_id = "toutiao"
    creator_url = CREATOR_PUBLISH_URL
    fixed_steps = (
        "open_creator_publish",
        "assert_logged_in",
        "fill_content",
        "click_publish",
        "wait_publish_result",
    )

    def run(self, page: Any, pack: PublishPack) -> dict[str, Any]:
        results: list[ScriptStepResult] = []
        evidence: dict[str, Any] = {}

        try:
            page.goto(self.creator_url, wait_until="domcontentloaded", timeout=90_000)
            sleep_ms(2500)
            self._dismiss_overlays(page)
            self.step_log(results, "open_creator_publish", True, page.url)
        except Exception as e:
            self.step_log(results, "open_creator_publish", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        ok_login, detail = self._wait_editor_ready(page)
        self.step_log(results, "assert_logged_in", ok_login, detail)
        if not ok_login:
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        title = (pack.title or "").strip()
        raw = ""
        if pack.output_dir:
            p = pack.output_dir / "publish" / "toutiao_micro.txt"
            if p.is_file():
                raw = p.read_text(encoding="utf-8").strip()
        if not raw:
            raw = (pack.body or pack.title or "").strip()
        if not title:
            title, _ = split_title_body(raw)
        content = format_toutiao_micro(title, raw)[:BODY_MAX]
        content_html = format_toutiao_micro_html(title, raw)
        needle = normalize_needle_from_title(title or content[:40])
        if not content:
            self.step_log(results, "fill_content", False, "正文为空")
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        try:
            filled = False
            for loc in (
                page.locator(".editor-kit-container [contenteditable]").first,
                page.locator('[contenteditable="true"]').first,
                page.get_by_role("textbox").first,
            ):
                try:
                    if loc.count() == 0:
                        continue
                    loc.wait_for(state="attached", timeout=20_000)
                    fill_editor_content(
                        page, loc, content, html=content_html[:8000] or None
                    )
                    filled = True
                    break
                except Exception:
                    continue
            if not filled:
                page.locator("body").click(position={"x": 480, "y": 420})
                sleep_ms(300)
                page.keyboard.type(content, delay=18)
            sleep_ms(1000)
            self.step_log(results, "fill_content", True, f"len={len(content)}")
        except Exception as e:
            self.step_log(results, "fill_content", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        try:
            self._dismiss_overlays(page)
            btn = self._find_publish_button(page)
            if not btn:
                raise RuntimeError("publish_button_not_found")
            btn.click(timeout=20_000)
            sleep_ms(1200)
            click_confirm_dialogs(page)
            sleep_ms(2000)
            click_confirm_dialogs(page)
            self.step_log(results, "click_publish", True)
        except Exception as e:
            self.step_log(results, "click_publish", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        confirmed, ev = self._wait_publish_success(page, needle)
        evidence.update(ev)
        self.step_log(results, "wait_publish_result", confirmed, ev.get("detail", ""))
        return self._out(results, ok=confirmed, evidence=evidence, pack=pack, page=page)

    def _find_publish_button(self, page: Any) -> Any | None:
        for sel in (
            page.get_by_role("button", name="发布"),
            page.locator('button:has-text("发布")'),
            page.locator('button:has-text("发表")'),
        ):
            try:
                for i in range(sel.count()):
                    btn = sel.nth(i)
                    if btn.is_visible() and not btn.is_disabled():
                        return btn
            except Exception:
                continue
        return None

    def _wait_publish_success(self, page: Any, needle: str) -> tuple[bool, dict[str, Any]]:
        deadline = time.time() + 90
        while time.time() < deadline:
            ok, ev = wait_for_toast_ok(
                page,
                timeout_ms=2_500,
                ok_patterns=("发布成功", "已发布", "提交成功", "发表成功", "审核中", "发送成功"),
            )
            if ok:
                ev["final_url"] = page.url
                return True, ev
            url = page.url or ""
            if "weitoutiao/publish" not in url and "mp.toutiao.com" in url:
                if page_contains_needle(page, needle):
                    return True, {"detail": "left_publish_with_text", "final_url": url}
            sleep_ms(700)
        return wait_manage_list_has_needle(page, LIST_URL, needle, timeout_ms=60_000)

    def _dismiss_overlays(self, page: Any) -> None:
        for txt in ("我知道了", "知道了", "关闭", "暂不"):
            loc = page.locator(f"text={txt}")
            if loc.count():
                try:
                    loc.first.click(timeout=2_000)
                    sleep_ms(300)
                except Exception:
                    pass

    def _wait_editor_ready(self, page: Any) -> tuple[bool, str]:
        deadline = time.time() + EDITOR_WAIT_MS / 1000.0
        while time.time() < deadline:
            url = page.url or ""
            url_l = url.lower()
            if "sso.toutiao.com" in url_l or "/auth/page/login" in url_l:
                return False, f"login_redirect:{url[:80]}"
            loc = page.locator(SEL_EDITOR)
            if loc.count() > 0:
                try:
                    if loc.first.is_visible():
                        return True, "editor_ready"
                except Exception:
                    return True, "editor_ready"
            sleep_ms(800)
        return False, f"editor_timeout:{url[:80]}"

    def _out(
        self,
        results: list[ScriptStepResult],
        *,
        ok: bool,
        evidence: dict[str, Any],
        pack: PublishPack | None = None,
        page: Any | None = None,
    ) -> dict[str, Any]:
        if not ok and page is not None and pack is not None:
            screenshot_on_fail(page, pack, "toutiao_last.png")
        return {
            "channel_id": self.channel_id,
            "ok": ok,
            "publish_confirmed": ok,
            "evidence": evidence,
            "steps": [r.__dict__ for r in results],
            "script": "toutiao_fixed_v4",
        }


class ToutiaoLoginScript:
    creator_url = CREATOR_PUBLISH_URL

    def check(self, page: Any) -> dict[str, Any]:
        page.goto(self.creator_url, wait_until="domcontentloaded", timeout=90_000)
        sleep_ms(3000)
        script = ToutiaoPublishScript()
        ok, detail = script._wait_editor_ready(page)
        return {
            "channel_id": "toutiao",
            "logged_in": ok,
            "need_login": not ok,
            "script": "toutiao_login_check_v2",
            "detail": detail,
        }
