"""电商场景（Phase 3 占位 + MVP 竖版裁剪）。"""
from __future__ import annotations

from ..manual_clip import process_manual_clip

ECOMMERCE_HINT = """
**规划中的电商能力（后续版本）**
- 按静音/停顿自动切讲解段
- 3:4 / 1:1 主图视频（≤15 秒）
- 卖点字幕模板（价格、优惠关键词高亮）
- 批量处理商品文件夹

**当前可用**：在下方填写时间段，导出 9:16 竖屏商品讲解短片（无需 API）。
"""


def process_ecommerce_clip(
    video_path,
    segments_text: str,
    aspect: str = "9:16",
):
    vertical = aspect.strip() in ("9:16", "vertical", "竖屏")
    status, out = process_manual_clip(video_path, segments_text, vertical_9_16=vertical)
    if status.startswith("✅"):
        status = f"{status}\n\n🛒 **电商切片（基础版）**\n{ECOMMERCE_HINT}"
    return status, out
