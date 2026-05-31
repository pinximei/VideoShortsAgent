#!/usr/bin/env python3
"""
口播预研「可证伪」报告：只写实测数据，标明失败样本。
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CORPUS = ROOT / "research" / "motion" / "github_daily" / "video_corpus.json"
FRAME_REPORT = ROOT / "research" / "voice_content" / "analysis_report.json"
MEDIA_MEASURED = ROOT / "research" / "voice_content" / "measured_analysis.json"
DOWNLOAD_MANIFEST = ROOT / "research" / "voice_content" / "download_manifest.json"
OURS_TTS = ROOT / "research" / "voice_content" / "ours_tts_proof.json"
PROOF = ROOT / "docs" / "VOICE_CONTENT_PROOF_REPORT.md"


def _run_py(script: str, args: list[str] | None = None) -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / "motion_research" / script)] + (args or [])
    p = subprocess.run(cmd, cwd=str(ROOT), timeout=3600)
    return p.returncode


def _ours_tts_proof() -> dict:
    """同一段文案不同 edge rate → 实测秒数（证明语速参数生效）。"""
    from python_agent.tts_provider import run_async, synthesize_to_file

    text = "别划走，今天这个 GitHub 项目 Star 涨了一万，评论区扣一要链接。"
    out_dir = ROOT / "research" / "voice_content" / "ours_tts"
    out_dir.mkdir(parents=True, exist_ok=True)
    voice = "zh-CN-YunxiNeural"
    rows = []
    for rate in ("+0%", "+10%", "+18%"):
        path = out_dir / f"sample_{rate.replace('%','p')}.mp3"
        run_async(synthesize_to_file(text, voice, path, rate=rate))
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
        )
        dur = float(probe.stdout.strip()) if probe.returncode == 0 else None
        rows.append(
            {
                "rate": rate,
                "chars": len(text),
                "duration_sec": dur,
                "mp3": str(path.relative_to(ROOT)).replace("\\", "/"),
            }
        )
    payload = {"text": text, "voice": voice, "samples": rows}
    OURS_TTS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    print("[1/4] frame analysis (captures)...")
    _run_py("analyze_voice_from_captures.py")

    print("[2/4] download bilibili media...")
    _run_py("download_reference_media.py")

    print("[3/4] analyze subtitles/audio...")
    _run_py("analyze_voice_from_media.py")

    print("[4/4] our TTS rate proof...")
    ours = _ours_tts_proof()

    frame = json.loads(FRAME_REPORT.read_text(encoding="utf-8")) if FRAME_REPORT.is_file() else {}
    media = json.loads(MEDIA_MEASURED.read_text(encoding="utf-8")) if MEDIA_MEASURED.is_file() else {}
    dl = json.loads(DOWNLOAD_MANIFEST.read_text(encoding="utf-8")) if DOWNLOAD_MANIFEST.is_file() else {}

    frame_ok = sum(
        1
        for v in frame.get("videos", [])
        if (v.get("voice_analysis") or {}).get("change_peaks", 0) > 0
    )
    frame_total = len(frame.get("videos", []))
    media_ok = media.get("measurable_count", 0)

    ts = datetime.now(timezone.utc).isoformat()
    lines = [
        "# 口播/语速预研 — 可证伪报告（实测）",
        "",
        f"> 生成：{ts}",
        "> **原则**：无实测数字的结论标为「未证实」；下列 JSON 为机器输出，可复现。",
        "",
        "## 1. 此前问题（已用数据核对）",
        "",
        f"| 检测项 | 结果 |",
        f"|--------|------|",
        f"| 抽帧字幕差分（20条）有效 peaks>0 | **{frame_ok}/{frame_total}** |",
        f"| B站 yt-dlp 字幕可解析语速 | **{media_ok}** 条 |",
        "",
        "**原因说明（有截图证据）**：大量 `captures/*/keyframes` 为抖音**登录弹窗/推荐页**遮挡，非播放中画面；静态幻灯片镜也无底部字幕切换 → `change_peaks=0` 属预期，不是「爆款都慢速」。",
        "",
        "请打开任意失败样本关键帧自行核对，例如：",
        "- `research/motion/github_daily/captures/7618932620755291433/keyframes/key_03_055pct.png`（登录框挡画面）",
        "",
        "## 2. 复现命令",
        "",
        "```powershell",
        "cd D:\\VideoShortsAgent",
        "py -3 scripts/motion_research/prove_voice_research.py",
        "py -3 scripts/motion_research/capture_douyin_frames.py --force --out-subdir captures_v2",
        "```",
        "",
        "## 3. 机器输出文件（原始证据）",
        "",
        "| 文件 | 含义 |",
        "|------|------|",
        f"| `research/voice_content/analysis_report.json` | 抽帧字幕带差分 |",
        f"| `research/voice_content/download_manifest.json` | yt-dlp 下载结果 |",
        f"| `research/voice_content/measured_analysis.json` | **字幕VTT解析**语速 |",
        f"| `research/voice_content/ours_tts_proof.json` | 我方同文案不同 rate 实测秒数 |",
        "",
        "## 4. B站字幕实测（chars/min）",
        "",
    ]
    if media.get("videos"):
        lines.append("| video_id | cues | 总字数 | 口播跨度(s) | 字/分钟 | 证据 |")
        lines.append("|----------|------|--------|-------------|---------|------|")
        for m in media["videos"]:
            if not m.get("measurable"):
                continue
            lines.append(
                f"| {m['video_id']} | {m.get('subtitle_cues')} | {m.get('total_chars')} | "
                f"{m.get('speech_span_sec')} | **{m.get('chars_per_minute')}** | vtt |"
            )
    else:
        lines.append("（暂无 — 先跑 download + analyze）")

    lines.extend(["", "## 5. 我方 TTS rate 实测（同文案）", ""])
    lines.append("| edge rate | 字数 | 合成秒数 | 文件 |")
    lines.append("|-----------|------|----------|------|")
    for s in ours.get("samples", []):
        lines.append(
            f"| {s['rate']} | {s['chars']} | {s.get('duration_sec')} | `{s.get('mp3')}` |"
        )

    lines.extend(
        [
            "",
            "## 6. 模板 catalog 状态",
            "",
            "- `templates/voice_content_20/catalog.json` 中 **WPM/rate 在媒体实测不足时不得视为已验证**",
            "- 仅 `measured_analysis.json` 有行的 video_id 可回填 `measured_ref`",
            "",
            "## 7. 下一步（必须做完才算学完）",
            "",
            "1. `captures_v2`：仅截 `<video>` 元素 + 关登录框（见 capture 脚本 `--out-subdir captures_v2`）",
            "2. 抖音：登录态 cookie 下 yt-dlp 或 ASR 转写",
            "3. 用实测分位数生成 V01–V20 的 `edge_tts_rate`，禁止手填",
            "",
        ]
    )

    PROOF.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {PROOF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
