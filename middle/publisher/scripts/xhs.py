"""小红书创作者中心 — 固定步骤脚本（非 LLM）。"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from .base import PlatformPublishScript, PublishPack, ScriptStepResult

CREATOR_PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official&target=video"
SEL_UPLOAD_CONTENT = "div.upload-content"
SEL_LOGIN_SCAN = "text=扫码登录"
SEL_POPOVER = "div.d-popover"
SEL_VIDEO_TAB = 'div.creator-tab:has-text("上传视频")'
SEL_UPLOAD_INPUT = ".upload-input"
SEL_FILE_INPUT = 'input[type="file"]'
SEL_TITLE_INPUT = "div.d-input input"
SEL_TITLE_FALLBACK = 'textarea, input[placeholder*="标题"]'
SEL_BODY_EDITOR = "div.ql-editor"
SEL_BODY_FALLBACK = '[role="textbox"]'
SEL_PUBLISH_NEW = "xhs-publish-btn"
SEL_PUBLISH_RED = ".publish-page-publish-btn button.bg-red"
SEL_PUBLISH_CE = 'button.ce-btn.bg-red:has-text("发布")'
SEL_TOAST_OK = "text=发布成功"
SEL_TOAST_OK2 = "text=笔记发布成功"
SEL_REUPLOAD = "text=重新上传"
TITLE_MAX = 20
BODY_MAX = 1000
UPLOAD_READY_TIMEOUT_MS = 600_000
PUBLISH_RESULT_TIMEOUT_MS = 90_000
SEL_TITLE_TOO_LONG = "div.title-container div.max_suffix"
SEL_BODY_TOO_LONG = "div.edit-container div.length-error"
SEL_FAIL_TOAST = "text=发布失败"


def _sleep_ms(ms: int) -> None:
    time.sleep(ms / 1000.0)


class XhsPublishScript(PlatformPublishScript):
    channel_id = "xhs"
    creator_url = CREATOR_PUBLISH_URL
    fixed_steps = (
        "open_creator_publish",
        "dismiss_overlays",
        "assert_logged_in",
        "select_video_tab",
        "upload_video_file",
        "wait_video_ready",
        "fill_title",
        "fill_body_and_tags",
        "assert_publish_enabled",
        "click_publish",
        "wait_publish_result",
    )

    def run(self, page: Any, pack: PublishPack) -> dict[str, Any]:
        results: list[ScriptStepResult] = []
        evidence: dict[str, Any] = {}

        try:
            page.goto(self.creator_url, wait_until="domcontentloaded", timeout=90_000)
            try:
                page.wait_for_selector(SEL_UPLOAD_CONTENT, timeout=60_000)
            except Exception:
                pass
            _sleep_ms(800)
            self.step_log(results, "open_creator_publish", True, page.url)
        except Exception as e:
            self.step_log(results, "open_creator_publish", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        self._dismiss_overlays(page, results)

        if page.locator(SEL_LOGIN_SCAN).count() > 0 or page.locator("text=登录").count() > 0:
            if not page.locator(SEL_UPLOAD_CONTENT).count():
                self.step_log(results, "assert_logged_in", False, "需要登录")
                return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
        self.step_log(results, "assert_logged_in", True)

        if not self._click_video_tab(page, results):
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        if not pack.video_path or not pack.video_path.is_file():
            self.step_log(results, "upload_video_file", False, "视频不存在")
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
        try:
            inp = page.locator(f"{SEL_UPLOAD_INPUT}, {SEL_FILE_INPUT}").first
            inp.wait_for(state="attached", timeout=30_000)
            inp.set_input_files(str(pack.video_path.resolve()))
            self.step_log(results, "upload_video_file", True, pack.video_path.name)
        except Exception as e:
            self.step_log(results, "upload_video_file", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        ready, detail = self._wait_video_ready(page)
        self.step_log(results, "wait_video_ready", ready, detail)
        if not ready:
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        title = (pack.title or " ").strip()[:TITLE_MAX] or " "
        try:
            loc = page.locator(SEL_TITLE_INPUT)
            if not loc.count():
                loc = page.locator(SEL_TITLE_FALLBACK)
            if loc.count():
                loc.first.click()
                loc.first.fill(title)
            self.step_log(results, "fill_title", True, title)
        except Exception as e:
            self.step_log(results, "fill_title", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        body = (pack.body or "").strip()[:BODY_MAX]
        title_loc = None
        try:
            title_loc = page.locator(SEL_TITLE_INPUT)
            if not title_loc.count():
                title_loc = page.locator(SEL_TITLE_FALLBACK)
            if body:
                editor = page.locator(SEL_BODY_EDITOR)
                if not editor.count():
                    editor = page.locator(SEL_BODY_FALLBACK)
                if editor.count():
                    editor.first.click()
                    editor.first.fill(body)
                    _sleep_ms(1000)
                    if title_loc.count():
                        title_loc.first.click()
            tags = _extract_hashtags(body)
            if tags and body:
                self._input_tags(page, tags[:5])
            err = self._form_validation_error(page)
            if err:
                self.step_log(results, "fill_body_and_tags", False, err)
                return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
            self.step_log(results, "fill_body_and_tags", True, f"len={len(body)} tags={len(tags)}")
        except Exception as e:
            self.step_log(results, "fill_body_and_tags", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        btn, enabled_detail, is_widget = self._find_publish_button(page)
        if not btn:
            self.step_log(results, "assert_publish_enabled", False, enabled_detail)
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)
        self.step_log(results, "assert_publish_enabled", True, enabled_detail)

        try:
            self._click_publish_button(page, btn, is_widget)
            _sleep_ms(1500)
            self._click_confirm_dialogs(page)
            _sleep_ms(2500)
            self.step_log(results, "click_publish", True)
        except Exception as e:
            self.step_log(results, "click_publish", False, str(e)[:200])
            return self._out(results, ok=False, evidence=evidence, pack=pack, page=page)

        confirmed, ev = self._wait_publish_success(page)
        ev["final_url"] = page.url or ev.get("final_url", "")
        evidence.update(ev)
        self.step_log(results, "wait_publish_result", confirmed, ev.get("detail", ""))
        return self._out(results, ok=confirmed, evidence=evidence, pack=pack, page=page)

    def _dismiss_overlays(self, page: Any, results: list[ScriptStepResult]) -> None:
        try:
            if page.locator(SEL_POPOVER).count():
                page.locator(SEL_POPOVER).first.evaluate("el => el.remove()")
            for txt in ("我知道了", "知道了", "关闭"):
                if page.locator(f"text={txt}").count():
                    page.locator(f"text={txt}").first.click()
                    _sleep_ms(300)
            self.step_log(results, "dismiss_overlays", True)
        except Exception as e:
            self.step_log(results, "dismiss_overlays", True, f"skip:{str(e)[:80]}")

    def _click_video_tab(self, page: Any, results: list[ScriptStepResult]) -> bool:
        try:
            page.wait_for_selector(SEL_UPLOAD_CONTENT, timeout=30_000)
            if page.locator(f"{SEL_UPLOAD_INPUT}, {SEL_FILE_INPUT}").count():
                self.step_log(results, "select_video_tab", True, "upload_input_visible")
                return True
            deadline = time.time() + 15
            while time.time() < deadline:
                self._dismiss_overlays(page, [])
                tabs = page.locator("div.creator-tab")
                for i in range(tabs.count()):
                    tab = tabs.nth(i)
                    try:
                        if not tab.is_visible():
                            continue
                        txt = (tab.inner_text() or "").strip()
                        if txt != "上传视频":
                            continue
                        tab.click(timeout=5_000)
                        _sleep_ms(700)
                        self.step_log(results, "select_video_tab", True, "creator-tab")
                        return True
                    except Exception:
                        continue
                _sleep_ms(250)
            self.step_log(results, "select_video_tab", True, "target=video_url")
            return True
        except Exception as e:
            self.step_log(results, "select_video_tab", False, str(e)[:200])
            return False

    def _wait_video_ready(self, page: Any) -> tuple[bool, str]:
        deadline = time.time() + UPLOAD_READY_TIMEOUT_MS / 1000.0
        last = ""
        while time.time() < deadline:
            btn, detail, _ = self._find_publish_button(page)
            last = detail
            if btn is not None:
                if page.locator(SEL_REUPLOAD).count():
                    return True, "reupload_visible"
                return True, detail
            _sleep_ms(1000)
        return False, f"timeout:{last}"

    def _find_publish_button(self, page: Any) -> tuple[Any | None, str, bool]:
        widgets = page.locator(SEL_PUBLISH_NEW)
        for i in range(widgets.count()):
            w = widgets.nth(i)
            try:
                if not w.is_visible():
                    continue
                is_pub = w.get_attribute("is-publish")
                if is_pub and str(is_pub).lower() == "false":
                    continue
                sub = w.get_attribute("submit-disabled")
                if sub and str(sub).lower() == "true":
                    return None, "xhs-publish-btn:disabled", False
                return w, "xhs-publish-btn", True
            except Exception:
                continue
        for sel, label in (
            (SEL_PUBLISH_RED, "bg-red"),
            (SEL_PUBLISH_CE, "ce-btn"),
        ):
            loc = page.locator(sel)
            for i in range(loc.count()):
                btn = loc.nth(i)
                try:
                    if not btn.is_visible():
                        continue
                    if btn.is_disabled():
                        return None, f"{label}:disabled", False
                    aria = btn.get_attribute("aria-disabled")
                    if aria and str(aria).lower() == "true":
                        return None, f"{label}:aria-disabled", False
                    return btn, label, False
                except Exception:
                    continue
        return None, "publish_button_not_found", False

    def _click_publish_button(self, page: Any, btn: Any, is_widget: bool) -> None:
        if is_widget:
            box = btn.bounding_box()
            if box:
                page.mouse.click(
                    box["x"] + box["width"] * 0.65,
                    box["y"] + box["height"] / 2,
                )
                return
        btn.click()

    def _click_confirm_dialogs(self, page: Any) -> None:
        for txt in ("确认发布", "确定", "声明原创", "我知道了"):
            loc = page.locator(f"button:has-text('{txt}')")
            if loc.count():
                try:
                    loc.first.click(timeout=3_000)
                    _sleep_ms(500)
                except Exception:
                    pass

    def _form_validation_error(self, page: Any) -> str:
        if page.locator(SEL_TITLE_TOO_LONG).count():
            return "title_too_long"
        if page.locator(SEL_BODY_TOO_LONG).count():
            return "body_too_long"
        if page.locator(SEL_FAIL_TOAST).count():
            return "publish_failed_toast"
        return ""

    def _input_tags(self, page: Any, tags: list[str]) -> None:
        editor = page.locator(SEL_BODY_EDITOR)
        if not editor.count():
            editor = page.locator(SEL_BODY_FALLBACK)
        if not editor.count():
            return
        el = editor.first
        for tag in tags:
            tag = tag.lstrip("#").strip()
            if not tag:
                continue
            try:
                el.type(f"#{tag} ", delay=30)
                _sleep_ms(600)
                topic = page.locator("#creator-editor-topic-container .item")
                if topic.count():
                    topic.first.click()
                    _sleep_ms(400)
            except Exception:
                continue

    def _wait_publish_success(self, page: Any) -> tuple[bool, dict[str, Any]]:
        ev: dict[str, Any] = {"detail": ""}
        deadline = time.time() + PUBLISH_RESULT_TIMEOUT_MS / 1000.0
        while time.time() < deadline:
            err = self._form_validation_error(page)
            if err:
                ev["detail"] = err
                return False, ev
            for sel in (
                SEL_TOAST_OK,
                SEL_TOAST_OK2,
                "text=已发布",
                "text=发布完成",
                "text=审核中",
                "text=上传成功",
            ):
                if page.locator(sel).count():
                    ev["toast"] = sel
                    ev["detail"] = "toast_ok"
                    return True, ev
            url = page.url or ""
            if "publish/publish" not in url and "creator.xiaohongshu.com" in url:
                ev["final_url"] = url
                ev["detail"] = "left_publish_page"
                return True, ev
            btn, detail, _ = self._find_publish_button(page)
            if btn is None and time.time() + 30 > deadline:
                ev["detail"] = "publish_button_gone"
                ev["final_url"] = url
                return True, ev
            _sleep_ms(800)
        err = self._form_validation_error(page)
        if not err:
            ev["detail"] = "assumed_ok_no_explicit_toast"
            ev["final_url"] = page.url
            return True, ev
        ev["detail"] = err or "no_success_signal"
        ev["final_url"] = page.url
        return False, ev

    def _screenshot_on_fail(self, page: Any, pack: PublishPack) -> None:
        if not pack.output_dir:
            return
        out = pack.output_dir / "publish" / "xhs_last.png"
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out), full_page=True)
        except Exception:
            pass

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
            self._screenshot_on_fail(page, pack)
        return {
            "channel_id": self.channel_id,
            "ok": ok,
            "publish_confirmed": ok,
            "evidence": evidence,
            "steps": [r.__dict__ for r in results],
            "script": "xhs_fixed_v2",
        }


def _extract_hashtags(text: str) -> list[str]:
    return re.findall(r"#([^\s#]{1,30})", text or "")


class XhsLoginScript:
    creator_url = "https://creator.xiaohongshu.com/"

    def check(self, page: Any) -> dict[str, Any]:
        page.goto(CREATOR_PUBLISH_URL, wait_until="domcontentloaded", timeout=90_000)
        _sleep_ms(3500)
        url = (page.url or "").lower()
        has_upload = page.locator(SEL_UPLOAD_CONTENT).count() > 0 or page.locator(SEL_FILE_INPUT).count() > 0
        scan_login = page.locator(SEL_LOGIN_SCAN).count() > 0
        login_url = "/login" in url
        on_creator = "creator.xiaohongshu.com" in url
        logged_in = has_upload or (on_creator and not scan_login and not login_url)
        return {
            "channel_id": "xhs",
            "logged_in": logged_in,
            "need_login": not logged_in,
            "script": "xhs_login_check_v2",
            "detail": (page.url or "")[:100],
        }
