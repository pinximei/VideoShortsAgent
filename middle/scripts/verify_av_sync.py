#!/usr/bin/env python3
"""对照 TTS 时间轴与成片时长，检查音画同步与 B-roll 起点。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(ROOT))

from python_agent.pipeline_render import allocate_broll_timings, clips_need_broll_retiming, _probe_duration
from python_agent.skills.dubbing_skill import DubbingSkill


def probe_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    return float((r.stdout or "0").strip())


def main() -> int:
    task = ROOT / "data/output/838"
    broll = ROOT / "data/assets/broll_template.mp4"
    if not task.is_dir():
        print(f"任务目录不存在: {task}", file=sys.stderr)
        return 1

    broll_dur = _probe_duration(str(broll))
    issues: list[str] = []

    for plat in ("xhs", "douyin"):
        plan_path = task / "llm" / f"video_clips_{plat}.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
        clips = [dict(c) for c in plan.get("clips") or []]
        fx = plan.get("effects") or {}
        td = float(fx.get("transition_duration", 0.35))
        voice = "zh-CN-XiaoxiaoNeural" if plat == "xhs" else "zh-CN-YunxiNeural"

        dub = DubbingSkill(voice=voice)
        tmp = task / "_verify_tts" / plat
        tmp.mkdir(parents=True, exist_ok=True)
        tts_info = dub.execute({"clips": clips}, str(tmp))
        tlist = tts_info.get("tts_clips") or []

        # 模拟 _trim_clips（60s 上限）
        max_s = 60.0
        kept_t, total = [], 0.0
        for t in tlist:
            dur = float(t.get("duration") or 0)
            if dur <= 0 or total + dur > max_s + 0.25:
                break
            kept_t.append(t)
            total += dur
        n = len(kept_t)
        tts_sum = sum(float(t.get("duration") or 0) for t in kept_t)
        expected_audio = tts_sum - max(0, n - 1) * td if n > 1 else tts_sum

        mp4 = task / "videos" / f"{plat}.mp4"
        actual = probe_duration(mp4)
        av_delta = actual - expected_audio

        clips_check = [dict(c) for c in clips[:n]]
        if clips_need_broll_retiming(clips_check):
            allocate_broll_timings(clips_check, kept_t, broll_dur)
        starts_used = [round(float(c["start"]), 2) for c in clips_check]
        broll_ok = len(set(starts_used)) > 1 or (len(starts_used) == 1 and starts_used[0] == 0)

        print(f"\n=== {plat}.mp4 (Remotion: {fx.get('use_remotion')}) ===")
        print(f"  成片时长: {actual:.2f}s")
        print(f"  TTS 段数: {n}（计划 {len(clips)} 段）")
        print(f"  TTS 时长合计: {tts_sum:.2f}s")
        print(f"  转场重叠约: {(n - 1) * td:.2f}s → 预期音轨约 {expected_audio:.2f}s")
        print(f"  音轨 vs 文件: Δ={av_delta:+.2f}s {'OK' if abs(av_delta) < 2.5 else 'WARN'}")
        print(f"  B-roll 起点(渲染后逻辑): {starts_used} {'OK' if broll_ok else 'WARN'}")
        if not broll_ok and n > 1:
            issues.append(f"{plat}: B-roll 多段起点未拉开")

        for i, t in enumerate(kept_t[:4]):
            sents = t.get("sentences") or []
            tdur = float(t.get("duration") or 0)
            if not sents:
                issues.append(f"{plat} seg{i}: 无 sentences，Remotion 字幕可能对不齐")
                continue
            last_end = float(sents[-1].get("end") or 0)
            drift = last_end - tdur
            print(
                f"  段{i}: TTS={tdur:.2f}s 末句end={last_end:.2f}s "
                f"字幕轴漂移={drift:+.2f}s {'OK' if abs(drift) < 0.5 else 'WARN'}"
            )

    print("\n=== 结论 ===")
    if issues:
        for x in issues:
            print(f"  ✗ {x}")
        print(
            "\n  段内：TTS 主时钟 + Remotion sentences → 口播与句级字幕通常对齐。"
            "\n  段间：音轨拼接正常；画面因 start=0 未分配，多段重复同一 B-roll 开头。"
        )
        return 1
    print("  未发现明显音画不同步（时长层面）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
