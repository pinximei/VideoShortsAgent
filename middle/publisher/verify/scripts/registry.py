"""发布后验收脚本注册。"""
from __future__ import annotations

from .douban import DoubanVerifyScript
from .douyin import DouyinVerifyScript
from .toutiao import ToutiaoVerifyScript
from .xhs import XhsVerifyScript

VERIFY_SCRIPTS = {
    "douyin": DouyinVerifyScript,
    "xhs": XhsVerifyScript,
    "toutiao": ToutiaoVerifyScript,
    "douban": DoubanVerifyScript,
}


def get_verify_script(channel_id: str):
    cls = VERIFY_SCRIPTS.get(channel_id)
    if not cls:
        raise ValueError(f"no verify script for channel: {channel_id}")
    return cls()
