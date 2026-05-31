"""抖音 / 竖屏短视频发布预设（无 API）。"""
from __future__ import annotations

from ..manual_clip import process_manual_clip

# 抖音常见规范（可在 Phase 2 做成可配置）
DEFAULT_MAX_SECONDS = 60.0
SAFE_HINT = (
    "建议单条成片 ≤60 秒；竖屏 9:16；重要字幕避开底部 15%（可能被 UI 遮挡）。"
)


def process_douyin_pack(video_path, segments_text: str, max_seconds: float = DEFAULT_MAX_SECONDS):
    """竖屏 + 时长校验 + 本地裁剪。"""
    from ..manual_clip import parse_segments

    try:
        clips = parse_segments(segments_text)
    except ValueError as e:
        return f"❌ {e}", None

    total = sum(c["end"] - c["start"] for c in clips)
    if total > max_seconds + 0.5:
        return (
            f"❌ 总时长 {total:.1f}s 超过抖音建议上限 {max_seconds:.0f}s，请减少段数或缩短区间。\n\n{SAFE_HINT}",
            None,
        )

    status, out = process_manual_clip(video_path, segments_text, vertical_9_16=True)
    if out:
        status = f"{status}\n\n📱 **抖音发布包**\n- 已导出 9:16 竖屏\n- {SAFE_HINT}"
    return status, out
