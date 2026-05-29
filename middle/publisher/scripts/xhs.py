"""小红书创作者中心 — 固定步骤脚本（非 LLM）。"""
from __future__ import annotations

import time
from typing import Any

from .base import PlatformPublishScript, PublishPack, ScriptStepResult

SEL_LOGIN = "text=登录"
SEL_PUBLISH_NOTE = "text=发布笔记"
SEL_UPLOAD_VIDEO = "text=上传视频"
SEL_FILE_INPUT = 'input[type="file"]'
SEL_TITLE = 'textarea, input[placeholder*="标题"]'
SEL_PUBLISH_BTN = 'button:has-text("发布")'


class XhsPublishScript(PlatformPublishScript):
    channel_id = "xhs"
    creator_url = "https://creator.xiaohongshu.com/publish/publish"
    fixed_steps = (
        "open_creator_publish",
        "assert_logged_in",
        "select_video_note",
        "upload_video_file",
        "fill_title",
        "click_publish",
    )

    def run(self, page: Any, pack: PublishPack) -> dict[str, Any]:
        results: list[ScriptStepResult] = []

        page.goto(self.creator_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)
        self.step_log(results, "open_creator_publish", True)

        if page.locator(SEL_LOGIN).count() > 0:
            self.step_log(results, "assert_logged_in", False, "需要登录")
            return self._out(results, ok=False)
        self.step_log(results, "assert_logged_in", True)

        try:
            if page.locator(SEL_UPLOAD_VIDEO).count():
                page.locator(SEL_UPLOAD_VIDEO).first.click()
                time.sleep(1)
            self.step_log(results, "select_video_note", True)
        except Exception as e:
            self.step_log(results, "select_video_note", False, str(e)[:200])
            return self._out(results, ok=False)

        if not pack.video_path or not pack.video_path.is_file():
            self.step_log(results, "upload_video_file", False, "视频不存在")
            return self._out(results, ok=False)
        try:
            page.locator(SEL_FILE_INPUT).first.set_input_files(str(pack.video_path))
            time.sleep(3)
            self.step_log(results, "upload_video_file", True)
        except Exception as e:
            self.step_log(results, "upload_video_file", False, str(e)[:200])
            return self._out(results, ok=False)

        try:
            if page.locator(SEL_TITLE).count():
                page.locator(SEL_TITLE).first.fill((pack.title or "")[:20])
            self.step_log(results, "fill_title", True)
        except Exception as e:
            self.step_log(results, "fill_title", False, str(e)[:200])
            return self._out(results, ok=False)

        try:
            if page.locator(SEL_PUBLISH_BTN).count():
                page.locator(SEL_PUBLISH_BTN).first.click()
                time.sleep(5)
            self.step_log(results, "click_publish", True)
        except Exception as e:
            self.step_log(results, "click_publish", False, str(e)[:200])
            return self._out(results, ok=False)

        return self._out(results, ok=True)

    def _out(self, results: list[ScriptStepResult], *, ok: bool) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "ok": ok,
            "steps": [r.__dict__ for r in results],
            "script": "xhs_fixed",
        }


class XhsLoginScript:
    creator_url = "https://creator.xiaohongshu.com/"

    def check(self, page: Any) -> dict[str, Any]:
        page.goto(self.creator_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)
        need_login = page.locator(SEL_LOGIN).count() > 0
        return {
            "channel_id": "xhs",
            "logged_in": not need_login,
            "need_login": need_login,
            "script": "xhs_login_check",
        }
