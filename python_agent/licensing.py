"""桌面版授权：免费版限额 + 离线 Pro 激活码。"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any

from .paths import app_data_dir

# 发行前请设置环境变量 VSA_LICENSE_SECRET；生成密钥见 tools/generate_license.py
_DEFAULT_SECRET = "video-shorts-agent-dev-secret-change-me"

FREE_AI_EXPORTS_PER_MONTH = 2
FREE_WATERMARK = "VideoShorts 免费版"


class LicenseError(Exception):
    pass


def _secret() -> bytes:
    return (os.getenv("VSA_LICENSE_SECRET") or _DEFAULT_SECRET).encode("utf-8")


def _license_path() -> str:
    return os.path.join(app_data_dir(), "license.json")


def _usage_path() -> str:
    return os.path.join(app_data_dir(), "usage.json")


def _machine_id() -> str:
    path = os.path.join(app_data_dir(), "machine_id.txt")
    if os.path.isfile(path):
        return open(path, encoding="utf-8").read().strip()
    mid = str(uuid.uuid4())
    with open(path, "w", encoding="utf-8") as f:
        f.write(mid)
    return mid


def _sign(customer: str) -> str:
    digest = hmac.new(_secret(), customer.strip().lower().encode("utf-8"), hashlib.sha256).hexdigest()
    return f"VSA1-{digest[:20].upper()}"


def generate_license_key(customer_id: str) -> str:
    """卖家工具：按客户标识生成激活码。"""
    return _sign(customer_id)


def verify_license_key(key: str) -> bool:
    k = (key or "").strip().upper()
    if not k.startswith("VSA1-") or len(k) < 10:
        return False
    # 通用 Pro 码（单密钥多机，适合早期售卖）
    if hmac.compare_digest(k, _sign("pro")):
        return True
    # 绑定机器码
    if hmac.compare_digest(k, _sign(_machine_id())):
        return True
    return False


def load_license() -> dict[str, Any]:
    path = _license_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_license(key: str) -> tuple[bool, str]:
    k = (key or "").strip()
    if not k:
        return False, "请输入激活码"
    if not verify_license_key(k):
        return False, "激活码无效，请核对后重试"
    data = {
        "edition": "pro",
        "key_hint": k[:8] + "…",
        "activated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(_license_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True, "已激活专业版"


def is_pro() -> bool:
    return load_license().get("edition") == "pro"


def edition_label() -> str:
    return "专业版" if is_pro() else "免费版"


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_usage() -> dict[str, Any]:
    path = _usage_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_usage(data: dict[str, Any]) -> None:
    with open(_usage_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ai_exports_this_month() -> int:
    usage = _load_usage()
    bucket = usage.get(_month_key()) or {}
    return int(bucket.get("ai_exports") or 0)


def check_feature(feature: str) -> None:
    """feature: manual_clip | ai_agent | ai_subtitle"""
    if feature == "manual_clip":
        return
    if is_pro():
        return
    if feature in ("ai_agent", "ai_subtitle"):
        if ai_exports_this_month() >= FREE_AI_EXPORTS_PER_MONTH:
            raise LicenseError(
                f"免费版本月 AI 导出已达 {FREE_AI_EXPORTS_PER_MONTH} 次。"
                f"请使用「本地裁剪」（无需 API），或在「授权」页激活专业版。"
            )
        return
    raise LicenseError("未知功能")


def _apply_watermark(src: str) -> str:
    base, ext = os.path.splitext(src)
    dst = f"{base}_free{ext or '.mp4'}"
    vf = (
        f"drawtext=text='{FREE_WATERMARK}':fontsize=22:fontcolor=white@0.55:"
        "borderw=2:bordercolor=black@0.4:x=20:y=h-th-20"
    )
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-vf", vf, "-c:a", "copy", dst],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if r.returncode != 0 or not os.path.isfile(dst):
        return src
    return dst


def record_export(video_path: str | None, *, feature: str) -> str | None:
    """成功导出后：计数、免费版加水印。"""
    if not video_path or not os.path.isfile(video_path):
        return video_path

    usage = _load_usage()
    bucket = usage.setdefault(_month_key(), {})
    if feature in ("ai_agent", "ai_subtitle"):
        bucket["ai_exports"] = int(bucket.get("ai_exports") or 0) + 1
    elif feature == "manual_clip":
        bucket["manual_exports"] = int(bucket.get("manual_exports") or 0) + 1
    _save_usage(usage)

    if is_pro():
        return video_path
    out = _apply_watermark(video_path)
    return out if os.path.isfile(out) else video_path


def license_status_markdown() -> str:
    mid = _machine_id()
    lines = [
        f"**当前版本**：{edition_label()}",
        f"**机器码**（发给卖家绑定激活码）：`{mid}`",
    ]
    if is_pro():
        lic = load_license()
        lines.append(f"**激活时间**：{lic.get('activated_at', '—')}")
    else:
        left = max(0, FREE_AI_EXPORTS_PER_MONTH - ai_exports_this_month())
        lines.append(
            f"**免费版**：本地裁剪不限次数；AI 精彩片段 / 中文字幕 本月剩余 **{left}** 次（导出带水印）。"
        )
        lines.append(f"**专业版**：不限次、无水印。激活码见 `tools/generate_license.py`。")
    return "\n\n".join(lines)
