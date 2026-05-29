"""抖音创作者中心 — 固定步骤脚本（非 LLM）。"""
from __future__ import annotations

import time
from typing import Any

from .base import PlatformPublishScript, PublishPack, ScriptStepResult

# 选择器随平台改版需人工更新；流程步骤固定不变。
SEL_LOGIN_INDICATOR = "text=扫码登录"  # 未登录时出现
SEL_CONTENT_MENU = "text=内容管理"
SEL_UPLOAD_ENTRY = "text=发布视频"
SEL_FILE_INPUT = 'input[type="file"]'
SEL_TITLE = 'textarea[placeholder*="标题"], input[placeholder*="标题"]'
SEL_PUBLISH_BTN = 'button:has-text("发布")'


class DouyinPublishScript(PlatformPublishScript):
    channel_id = "douyin"
    creator_url = "https://creator.douyin.com/creator-micro/home"
    fixed_steps = (
        "open_creator_home",
        "assert_logged_in",
        "goto_content_upload",
        "upload_video_file",
        "fill_title_and_tags",
        "click_publish",
        "wait_publish_result",
    )

    def run(self, page: Any, pack: PublishPack) -> dict[str, Any]:
        results: list[ScriptStepResult] = []

        # 1. 打开发布后台
        page.goto(self.creator_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)
        self.step_log(results, "open_creator_home", True)

        # 2. 登录检查
        if page.locator(SEL_LOGIN_INDICATOR).count() > 0:
            self.step_log(results, "assert_logged_in", False, "需要登录，请用 login 模式先扫码")
            return self._out(results, ok=False)

        self.step_log(results, "assert_logged_in", True)

        # 3. 进入内容上传（固定菜单路径，可按实际后台调整选择器）
        try:
            if page.locator(SEL_CONTENT_MENU).count():
                page.locator(SEL_CONTENT_MENU).first.click()
                time.sleep(1)
            if page.locator(SEL_UPLOAD_ENTRY).count():
                page.locator(SEL_UPLOAD_ENTRY).first.click()
                time.sleep(2)
            self.step_log(results, "goto_content_upload", True)
        except Exception as e:
            self.step_log(results, "goto_content_upload", False, str(e)[:200])
            return self._out(results, ok=False)

        # 4. 上传视频
        if not pack.video_path or not pack.video_path.is_file():
            self.step_log(results, "upload_video_file", False, f"视频不存在: {pack.video_path}")
            return self._out(results, ok=False)
        try:
            page.locator(SEL_FILE_INPUT).first.set_input_files(str(pack.video_path))
            time.sleep(3)
            self.step_log(results, "upload_video_file", True, str(pack.video_path.name))
        except Exception as e:
            self.step_log(results, "upload_video_file", False, str(e)[:200])
            return self._out(results, ok=False)

        # 5. 填标题
        try:
            title = pack.title or " "
            if page.locator(SEL_TITLE).count():
                page.locator(SEL_TITLE).first.fill(title[:55])
            self.step_log(results, "fill_title_and_tags", True)
        except Exception as e:
            self.step_log(results, "fill_title_and_tags", False, str(e)[:200])
            return self._out(results, ok=False)

        # 6. 发布
        try:
            if page.locator(SEL_PUBLISH_BTN).count():
                page.locator(SEL_PUBLISH_BTN).first.click()
                time.sleep(5)
            self.step_log(results, "click_publish", True)
            self.step_log(results, "wait_publish_result", True, "已点击发布，请在后台确认状态")
        except Exception as e:
            self.step_log(results, "click_publish", False, str(e)[:200])
            return self._out(results, ok=False)

        return self._out(results, ok=True)

    def _out(self, results: list[ScriptStepResult], *, ok: bool) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "ok": ok,
            "steps": [r.__dict__ for r in results],
            "script": "douyin_fixed",
        }


class DouyinLoginScript:
    """登录检查 / 保持会话：打开创作者中心检测是否已登录。"""

    creator_url = DouyinPublishScript.creator_url

    def check(self, page: Any) -> dict[str, Any]:
        page.goto(self.creator_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)
        need_login = page.locator(SEL_LOGIN_INDICATOR).count() > 0
        return {
            "channel_id": "douyin",
            "logged_in": not need_login,
            "need_login": need_login,
            "script": "douyin_login_check",
        }
