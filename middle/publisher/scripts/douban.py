"""豆瓣 — 日记/笔记固定步骤脚本（非 LLM）。"""
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
from .format_copy import format_douban_note, format_douban_note_html

# note/create 会 302 到此处；subtype=note 即「写日记」编辑器（App 我的日记可见）
CREATOR_PUBLISH_URL = "https://www.douban.com/topic/create?subtype=note"
CREATOR_PUBLISH_URL_ALT = "https://www.douban.com/note/create"
SEL_LOGIN = "text=登录豆瓣"
SEL_TITLE = (
    'input[name="db[note][title]"], #note_title, '
    'input[placeholder*="标题"]'
)
SEL_BODY = (
    'textarea[name="db[note][note]"], #note_text, #note_content, '
    'div[contenteditable="true"], .note-editor textarea, '
    'iframe[name="editor"] ~ textarea, textarea'
)
SEL_PUBLISH_BTN = (
    'button:has-text("发布"), button:has-text("发广播"), '
    'input[value="发布"], button:has-text("马上发布")'
)
BODY_MAX = 2000
TITLE_MAX = 80


def _wait_editor_spa(page: Any, *, timeout_ms: int = 120_000) -> None:
    """等待日记/话题编辑器就绪（note/create 与 topic SPA 结构不同）。"""
    import time

    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        try:
            if page.get_by_placeholder("请输入标题").count() or page.get_by_placeholder(
                "此刻你想分享"
            ).count():
                return
            if page.locator(SEL_TITLE).count() and (
                page.locator(SEL_BODY).count()
                or page.locator('[contenteditable="true"]').count()
                or page.get_by_role("textbox").count() >= 2
            ):
                return
            root = page.locator("#group-editor-root")
            if root.count():
                txt = root.inner_text(timeout=3_000)
                if txt and "加载中" not in txt:
                    if page.locator("textarea").count() > 0:
                        return
                    if page.locator('[contenteditable="true"]').count() > 0:
                        return
                    if page.get_by_role("textbox").count() >= 1:
                        return
        except Exception:
            pass
        sleep_ms(1000)
    raise RuntimeError("douban_editor_stuck_loading")


class DoubanPublishScript(PlatformPublishScript):
    channel_id = "douban"
    creator_url = CREATOR_PUBLISH_URL
    fixed_steps = (
        "open_note_create",
        "assert_logged_in",
        "fill_title",
        "fill_body",
        "click_publish",
        "wait_publish_result",
    )

    def run(self, page: Any, pack: PublishPack) -> dict[str, Any]:
        results: list[ScriptStepResult] = []
        evidence: dict[str, Any] = {}

        opened = False
        # 仅日记入口；topic/create 发的是话题，App「我的日记」里看不到
        for url in (self.creator_url,):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                _wait_editor_spa(page)
                url_now = page.url or ""
                if "accounts.douban.com/login" in url_now:
                    continue
                opened = True
                break
            except Exception:
                continue
        if not opened:
            self.step_log(results, "open_note_create", False, "open_failed")
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
        self.step_log(results, "open_note_create", True, page.url)

        url = page.url or ""
        has_form = page.locator(SEL_TITLE).count() > 0 or page.locator(SEL_BODY).count() > 0
        login_redirect = "accounts.douban.com/login" in url or "/login" in url
        if login_redirect or (page.locator(SEL_LOGIN).count() > 0 and not has_form):
            self.step_log(results, "assert_logged_in", False, "需要登录豆瓣")
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
        self.step_log(results, "assert_logged_in", True, url[:80])

        raw = ""
        if pack.output_dir:
            p = pack.output_dir / "publish" / "douban_note.txt"
            if p.is_file():
                raw = p.read_text(encoding="utf-8").strip()
        if not raw:
            raw = (pack.body or "").strip()
        title, body = split_title_body(raw)
        if pack.title:
            title = pack.title.strip()[:TITLE_MAX]
        if not title and body:
            title = body.splitlines()[0][:TITLE_MAX] if body else "笔记"
        body = format_douban_note(title, raw)
        body_html = format_douban_note_html(title, raw)
        if not body:
            self.step_log(results, "fill_body", False, "正文为空")
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        try:
            title_filled = False
            for ph in ("请输入标题", "标题"):
                loc = page.get_by_placeholder(ph)
                if loc.count():
                    loc.first.click(timeout=10_000)
                    loc.first.fill(title[:TITLE_MAX])
                    title_filled = True
                    break
            if not title_filled:
                tloc = page.locator(SEL_TITLE)
                if tloc.count():
                    tloc.first.fill(title[:TITLE_MAX])
                    title_filled = True
                else:
                    ce = page.locator('[contenteditable="true"]')
                    if ce.count() >= 1:
                        ce.first.click()
                        page.keyboard.type(title[:TITLE_MAX], delay=12)
                        title_filled = True
            if not title_filled:
                raise RuntimeError("title_field_not_found")
            self.step_log(results, "fill_title", True, title[:40])
        except Exception as e:
            self.step_log(results, "fill_title", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        sleep_ms(1200)

        try:
            filled = False
            hint = page.get_by_text("此刻你想分享", exact=False)
            if hint.count():
                hint.first.click(timeout=10_000)
                sleep_ms(400)
                filled = True
            ce = page.locator(
                '.public-DraftEditor-content[contenteditable="true"], '
                'div[contenteditable="true"]'
            )
            if ce.count():
                target = ce.last
                target.click(timeout=10_000)
                sleep_ms(400)
                filled = True
            if filled:
                page.keyboard.press("Control+A")
                sleep_ms(80)
                for i, line in enumerate(body[:BODY_MAX].splitlines()):
                    if line.strip():
                        page.keyboard.type(line, delay=6)
                    if i < len(body.splitlines()) - 1:
                        page.keyboard.press("Enter")
                        sleep_ms(40)
            if not filled:
                raise RuntimeError("no_visible_body_editor")
            sleep_ms(800)
            ce_check = page.locator('[contenteditable="true"]')
            body_text = ""
            for i in range(ce_check.count()):
                body_text += (ce_check.nth(i).inner_text(timeout=3_000) or "")
            if len(body_text.replace(title, "").strip()) < 30:
                raise RuntimeError("body_not_entered")
            self.step_log(results, "fill_body", True, f"len={len(body)}")
        except Exception as e:
            self.step_log(results, "fill_body", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        try:
            clicked = False
            candidates = page.locator('button:has-text("发布"), input[value="发布"]')
            for i in range(candidates.count() - 1, -1, -1):
                btn = candidates.nth(i)
                try:
                    if btn.is_visible() and not btn.is_disabled():
                        btn.click(timeout=15_000)
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                btn = page.get_by_role("button", name="发布")
                if btn.count() and btn.last.is_visible():
                    btn.last.click(timeout=15_000)
                    clicked = True
            if not clicked:
                raise RuntimeError("publish_button_not_found")
            sleep_ms(1500)
            click_confirm_dialogs(page)
            sleep_ms(4000)
            self.step_log(results, "click_publish", True)
        except Exception as e:
            self.step_log(results, "click_publish", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        confirmed, ev = self._wait_publish_success(page, title)
        evidence.update(ev)
        self.step_log(results, "wait_publish_result", confirmed, ev.get("detail", ""))
        return self._out(results, ok=confirmed, evidence=evidence, pack=pack, page=page)

    def _wait_publish_success(self, page: Any, title: str) -> tuple[bool, dict[str, Any]]:
        import re

        try:
            page.wait_for_url(
                re.compile(r".*douban\.com/note/\d+.*"),
                timeout=45_000,
            )
            url = page.url or ""
            if "create" not in url:
                return True, {"detail": "note_url", "final_url": url}
        except Exception:
            pass

        deadline = time.time() + 90
        while time.time() < deadline:
            url = page.url or ""
            if re.search(r"douban\.com/note/\d+", url) and "create" not in url:
                return True, {"detail": "note_url", "final_url": url}
            for bad in ("发布失败", "内容不能为空", "标题不能为空", "请先登录"):
                if page.locator(f"text={bad}").count():
                    return False, {"detail": f"publish_error:{bad}", "final_url": url}
            ok, ev = wait_for_toast_ok(
                page,
                timeout_ms=8_000,
                ok_patterns=(
                    "发布成功",
                    "已发布",
                    "提交成功",
                    "发送成功",
                    "发表成功",
                ),
            )
            if ok:
                ev["final_url"] = page.url
                return True, ev
            if page_contains_needle(page, "发布成功") or page_contains_needle(
                page, "已发布"
            ):
                return True, {"detail": "page_text_已发布", "final_url": url}
            sleep_ms(800)

        notes_url = ""
        try:
            m = re.search(r"douban\.com/people/([^/]+)/", page.url or "")
            if m:
                notes_url = f"https://www.douban.com/people/{m.group(1)}/notes"
        except Exception:
            pass
        if not notes_url:
            notes_url = "https://www.douban.com/mine/notes"
        listed, ev = wait_manage_list_has_needle(
            page,
            notes_url,
            title,
            timeout_ms=30_000,
            allow_generic_needles=False,
            require_list_item=True,
        )
        if listed:
            ev["detail"] = "notes_list_item_match"
            return True, ev
        ev["detail"] = "publish_no_redirect"
        ev["final_url"] = page.url
        return False, ev

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
            screenshot_on_fail(page, pack, "douban_last.png")
        return {
            "channel_id": self.channel_id,
            "ok": ok,
            "publish_confirmed": ok,
            "evidence": evidence,
            "steps": [r.__dict__ for r in results],
            "script": "douban_fixed_v2",
        }


class DoubanLoginScript:
    creator_url = CREATOR_PUBLISH_URL

    def check(self, page: Any) -> dict[str, Any]:
        page.goto(self.creator_url, wait_until="domcontentloaded", timeout=90_000)
        _wait_editor_spa(page, timeout_ms=60_000)
        url = page.url or ""
        url_l = url.lower()
        has_form = page.locator(SEL_TITLE).count() > 0 or page.locator(SEL_BODY).count() > 0
        login_redirect = "accounts.douban.com/login" in url_l or "/login" in url_l.split("douban.com")[-1][:20]
        on_create = "note/create" in url_l
        on_douban = "douban.com" in url_l
        logged_in = (has_form or on_create or on_douban) and not login_redirect
        return {
            "channel_id": "douban",
            "logged_in": logged_in,
            "need_login": not logged_in,
            "script": "douban_login_check_v1",
            "detail": url[:100],
        }
