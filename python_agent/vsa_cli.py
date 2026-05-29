"""
VSA 命令行入口（可打包为 EXE）。

中间层同步调用时直接用 vsa_render.render_from_plan；
跨进程/EXE 时传 JSON 参数文件。

示例::
    python -m python_agent.vsa_cli \\
        --plan task/llm/video_clips_douyin.json \\
        --broll D:/broll.mp4 \\
        --output task/videos/douyin.mp4 \\
        --platform douyin
"""
from __future__ import annotations

import argparse
import json
import sys

PLATFORM_DEFAULTS = {
    "douyin": {"voice": "zh-CN-YunxiNeural", "width": 1080, "height": 1920, "max_seconds": 60},
    "xhs": {"voice": "zh-CN-XiaoxiaoNeural", "width": 1080, "height": 1920, "max_seconds": 60},
}


def main() -> int:
    p = argparse.ArgumentParser(description="VSA 视频裁剪（接收中间层参数）")
    p.add_argument("--plan", required=True, help="分镜 JSON（llm/video_clips_*.json）")
    p.add_argument("--broll", required=True, help="B-roll 视频路径")
    p.add_argument("--output", "-o", required=True, help="输出 mp4")
    p.add_argument("--platform", default="douyin", choices=("douyin", "xhs"))
    p.add_argument("--skip-tts", action="store_true")
    p.add_argument("--json-out", help="将结果写入文件而非 stdout")
    args = p.parse_args()

    from python_agent.vsa_render import render_from_plan_file

    defaults = PLATFORM_DEFAULTS.get(args.platform, PLATFORM_DEFAULTS["douyin"])
    try:
        result = render_from_plan_file(
            args.plan,
            args.broll,
            args.output,
            platform=args.platform,
            skip_tts=args.skip_tts,
            **defaults,
        )
        payload = json.dumps(result, ensure_ascii=False)
        if args.json_out:
            open(args.json_out, "w", encoding="utf-8").write(payload)
        else:
            print(payload)
        return 0
    except Exception as e:
        err = json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
