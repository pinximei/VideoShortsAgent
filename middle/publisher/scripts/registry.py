"""按 channel_id 注册固定脚本；扩展新平台时在此注册。"""
from __future__ import annotations

from .douyin import DouyinLoginScript, DouyinPublishScript
from .xhs import XhsLoginScript, XhsPublishScript

PUBLISH_SCRIPTS = {
    "douyin": DouyinPublishScript,
    "xhs": XhsPublishScript,
}

LOGIN_SCRIPTS = {
    "douyin": DouyinLoginScript,
    "xhs": XhsLoginScript,
}


def get_publish_script(channel_id: str):
    cls = PUBLISH_SCRIPTS.get(channel_id)
    if not cls:
        raise ValueError(f"no fixed publish script for channel: {channel_id}")
    return cls()


def get_login_script(channel_id: str):
    cls = LOGIN_SCRIPTS.get(channel_id)
    if not cls:
        raise ValueError(f"no fixed login script for channel: {channel_id}")
    return cls()
