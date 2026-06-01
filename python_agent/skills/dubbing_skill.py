"""
DubbingSkill - 中文配音技能（句级精确同步）

按句子拆分 tts_text → 逐句生成 TTS → 拼接成完整音频。
返回每句话的精确起止时间，用于字幕精确同步。
"""
import os
import re
import json
import subprocess
import sys
from pathlib import Path


VOICE_MALE = "zh-CN-YunxiNeural"
VOICE_FEMALE = "zh-CN-XiaoxiaoNeural"
DEFAULT_VOICE = "zh-CN-YunyangNeural"  # 男声默认用云扬（比 Yunxi 更利落）；女声请显式传 Xiaoxiao

# 句间停顿（秒）
SENTENCE_PAUSE = 0.2
# 音频无法居中时的最小前置留白（秒）
MIN_LEAD_SILENCE = 0.3
# 前置留白上限（秒）,切换场景后应尽快出声
MAX_LEAD_SILENCE = 0.5
# 第 1 镜：几乎零留白，钩子口播立刻进
OPENING_LEAD_SILENCE = 0.06


def _safe_remove(path: str, *, retries: int = 6) -> None:
    import time

    if not path:
        return
    for attempt in range(retries):
        try:
            if os.path.exists(path):
                os.remove(path)
            return
        except PermissionError:
            if attempt >= retries - 1:
                raise
            time.sleep(0.35)


class DubbingSkill:
    """中文配音技能（句级精确同步）"""

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        *,
        tts_rate: str = "+0%",
        tts_pitch: str = "+0Hz",
        sentence_pause: float | None = None,
    ):
        self.voice = voice
        self.tts_rate = (tts_rate or "+0%").strip()
        self.tts_pitch = (tts_pitch or "+0Hz").strip()
        self.sentence_pause = sentence_pause if sentence_pause is not None else SENTENCE_PAUSE
        print(
            f"[DubbingSkill] 语音: {self.voice} rate={self.tts_rate} pitch={self.tts_pitch} OK"
        )

    def execute(self, analysis: dict, output_dir: str, voice: str = "") -> dict:
        """执行 TTS 生成（按句分段，精确计时）

        Args:
            voice: 可选，语音角色名称（如 'zh-CN-YunyangNeural'），为空时使用初始化时的默认值

        Returns:
            {
                "tts_clips": [{
                    "path": "tts_clip_0.mp3",
                    "duration": 12.5,
                    "sentences": [
                        {"text": "第一句", "start": 0.0, "end": 3.2},
                        {"text": "第二句", "start": 3.4, "end": 6.1},
                        ...
                    ]
                }, ...]
            }
        """
        # 如果指定了 voice，临时覆盖
        original_voice = self.voice
        if voice:
            self.voice = voice
            print(f"[DubbingSkill] 使用指定语音: {self.voice}")

        tts_dir = os.path.join(output_dir, "tts_segments")
        os.makedirs(tts_dir, exist_ok=True)

        # 兼容多种输入格式：list of slides, dict with "clips", dict with "slides"
        if isinstance(analysis, list):
            clips = analysis
        elif isinstance(analysis, dict):
            clips = analysis.get("clips", analysis.get("slides", []))
        else:
            clips = []
        clips_with_tts = [c for c in clips if c.get("tts_text")]

        if not clips_with_tts:
            print("[DubbingSkill] WARN: clips 中无 tts_text 字段")
            return {"tts_clips": []}

        print(f"[DubbingSkill] 开始生成 TTS: {len(clips_with_tts)} 个片段")

        clip_jobs: list[tuple[int, dict]] = []
        for i, clip in enumerate(clips):
            if (clip.get("tts_text") or "").strip():
                clip_jobs.append((i, clip))

        def _one_clip(job: tuple[int, dict]) -> dict | None:
            i, clip = job
            tts_text = clip["tts_text"]
            print(f"  [片段 {i+1}/{len(clips_with_tts)}] {tts_text[:60]}...")
            sentences = self._split_sentences(tts_text)
            sentence_audios = self._generate_tts_batch(sentences, tts_dir, i)
            if not sentence_audios:
                return None
            clip_audio_path = os.path.join(tts_dir, f"tts_clip_{i}.mp3")
            video_duration = float(clip.get("end", 0)) - float(clip.get("start", 0))
            sentence_timeline, total_duration = self._concat_sentence_audios(
                sentence_audios,
                clip_audio_path,
                tts_dir,
                i,
                video_duration,
                lead_silence_override=OPENING_LEAD_SILENCE if i == 0 else None,
            )
            if total_duration <= 0:
                total_duration = self._get_audio_duration(clip_audio_path)
            if sys.platform != "win32":
                for sa in sentence_audios:
                    _safe_remove(sa.get("path") or "")
            print(f"  → {len(sentence_audios)} 句, {total_duration:.1f}s")
            return {
                "path": clip_audio_path,
                "duration": total_duration,
                "sentences": sentence_timeline,
                "index": i,
            }

        if not clip_jobs:
            print("[DubbingSkill] WARN: clips 中无 tts_text 字段")
            return {"tts_clips": []}

        tts_clips: list[dict] = []
        jobs = clip_jobs
        if len(jobs) <= 1 or sys.platform == "win32":
            for job in jobs:
                row = _one_clip(job)
                if row:
                    tts_clips.append(row)
        else:
            import concurrent.futures
            from python_agent.config import get_config

            workers = min(get_config().tts_clip_workers, len(jobs))
            if sys.platform == "win32":
                workers = 1
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                futs = [pool.submit(_one_clip, job) for job in jobs]
                for fut in concurrent.futures.as_completed(futs):
                    row = fut.result()
                    if row:
                        tts_clips.append(row)
            tts_clips.sort(key=lambda x: int(x.get("index", 0)))

        # 恢复原始语音设置
        self.voice = original_voice

        if len(tts_clips) < len(clip_jobs):
            raise RuntimeError(
                f"tts_partial_failure: {len(tts_clips)}/{len(clip_jobs)} clips synthesized"
            )

        print(f"\n[DubbingSkill] OK: {len(tts_clips)} TTS clips (sentence timing)")
        return {"tts_clips": tts_clips}

    def _split_sentences(self, text: str) -> list:
        """按口播单行字幕粒度拆分（与底栏逐句显示对齐）。"""
        from python_agent.display_text import split_spoken_phrases

        phrases = split_spoken_phrases(text)
        return phrases if phrases else [text.strip() or text]

    def _concat_sentence_audios(
        self,
        sentence_audios: list,
        output_path: str,
        tts_dir: str,
        clip_index: int,
        video_duration: float = 0,
        *,
        lead_silence_override: float | None = None,
    ) -> tuple:
        """拼接句子音频，居中对齐于视频画面（前后留白），返回精确时间轴和总时长

        Args:
            video_duration: 视频画面时长（秒），用于计算居中留白

        Returns:
            (timeline, total_duration)
            timeline: [{"text": "...", "start": 0.0, "end": 3.2}, ...]
            total_duration: 包含前后留白的总时长
        """
        # 计算语音内容时长（句子 + 句间停顿）
        content_duration = sum(sa["duration"] for sa in sentence_audios)
        content_duration += self.sentence_pause * max(0, len(sentence_audios) - 1)

        # 计算前后留白：前留白 ≤ 0.5 秒（快速出声），剩余放尾部
        if video_duration > 0 and video_duration > content_duration:
            total_padding = video_duration - content_duration
            lead_silence = min(total_padding / 2, MAX_LEAD_SILENCE)
            trail_silence = total_padding - lead_silence

        else:
            lead_silence = (
                lead_silence_override
                if lead_silence_override is not None
                else (OPENING_LEAD_SILENCE if clip_index == 0 else MIN_LEAD_SILENCE)
            )
            trail_silence = 0.0

        # 生成静音文件
        silence_path = os.path.join(tts_dir, f"silence_{clip_index}.mp3")
        self._generate_silence(silence_path, self.sentence_pause)

        lead_silence_path = os.path.join(tts_dir, f"lead_{clip_index}.mp3")
        self._generate_silence(lead_silence_path, lead_silence)

        temp_files = [silence_path, lead_silence_path]

        # 构建拼接列表：前留白 + 句子（句间停顿） + 后留白
        def _to_ffmpeg_path(p):
            """转为 FFmpeg 兼容的绝对路径（正斜杠）"""
            return os.path.abspath(p).replace("\\", "/")

        concat_list_path = os.path.join(tts_dir, f"concat_{clip_index}.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f:
            f.write("file '" + _to_ffmpeg_path(lead_silence_path) + "'\n")
            for j, sa in enumerate(sentence_audios):
                f.write("file '" + _to_ffmpeg_path(sa["path"]) + "'\n")
                if j < len(sentence_audios) - 1:
                    f.write("file '" + _to_ffmpeg_path(silence_path) + "'\n")
            # 添加尾部留白
            if trail_silence > 0.05:
                trail_silence_path = os.path.join(tts_dir, f"trail_{clip_index}.mp3")
                self._generate_silence(trail_silence_path, trail_silence)
                f.write("file '" + _to_ffmpeg_path(trail_silence_path) + "'\n")
                temp_files.append(trail_silence_path)

        temp_files.append(concat_list_path)

        # FFmpeg concat（重编码避免 silence 和 edge-tts 的 codec 不匹配）
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path, "-c:a", "libmp3lame", "-b:a", "128k",
            output_path
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                raise RuntimeError(
                    f"tts_concat_failed clip={clip_index} rc={r.returncode}: {(r.stderr or '')[-200:]}"
                )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"tts_concat_failed clip={clip_index}: {e}") from e

        if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 80:
            raise RuntimeError(f"tts_concat_empty clip={clip_index}")

        # 计算每句的精确时间轴（偏移前留白）
        timeline = []
        current_time = lead_silence
        for j, sa in enumerate(sentence_audios):
            start = current_time
            end = start + sa["duration"]
            row = {
                "text": sa["text"],
                "start": round(start, 3),
                "end": round(end, 3),
            }
            if sa.get("words"):
                row["words"] = [
                    {
                        "text": w.get("text", ""),
                        "start": round(start + float(w.get("start", 0)), 3),
                        "end": round(start + float(w.get("end", 0)), 3),
                    }
                    for w in sa["words"]
                    if w.get("text")
                ]
            timeline.append(row)
            current_time = end + (self.sentence_pause if j < len(sentence_audios) - 1 else 0)

        # 总时长 = 最后一句结束 + 尾部留白
        total_duration = (timeline[-1]["end"] if timeline else 0) + trail_silence

        # 清理临时文件
        for path in temp_files:
            if os.path.exists(path):
                os.remove(path)

        return timeline, total_duration

    def _generate_silence(self, output_path: str, duration: float):
        """生成静音音频文件"""
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"anullsrc=r=24000:cl=mono",
            "-t", str(duration), "-c:a", "libmp3lame",
            output_path
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except Exception:
            pass

    def _tts_cache_dir(self, tts_dir: str) -> str:
        """任务级 TTS 缓存（跨片段复用相同句子）。"""
        root = Path(tts_dir).resolve().parent
        cache = root / "tts_cache"
        cache.mkdir(parents=True, exist_ok=True)
        return str(cache)

    def _generate_tts_batch(self, sentences: list, tts_dir: str, clip_index: int) -> list:
        """顺序生成各句 TTS（限流 + 重试），避免 gather 触发 503。"""
        from python_agent.tts_edge import word_boundaries_enabled
        from python_agent.tts_provider import run_async, synthesize_batch_sequential

        paths = [os.path.join(tts_dir, f"sent_{clip_index}_{j}.mp3")
                 for j in range(len(sentences))]
        items = list(zip(sentences, paths))
        cache_dir = self._tts_cache_dir(tts_dir)
        use_wb = word_boundaries_enabled()
        try:
            if use_wb:
                from python_agent.tts_edge import synthesize_to_file_with_words

                results = []
                for sentence, path in items:
                    _out, words = run_async(
                        synthesize_to_file_with_words(
                            sentence,
                            self.voice,
                            path,
                            cache_dir=cache_dir,
                            rate=self.tts_rate,
                            pitch=self.tts_pitch,
                        )
                    )
                    if os.path.exists(path) and os.path.getsize(path) > 80:
                        results.append(
                            {
                                "text": sentence,
                                "path": path,
                                "duration": self._get_audio_duration(path),
                                "words": words,
                            }
                        )
            else:
                run_async(
                    synthesize_batch_sequential(
                        items,
                        voice=self.voice,
                        cache_dir=cache_dir,
                        rate=self.tts_rate,
                        pitch=self.tts_pitch,
                    )
                )
                results = []
                for sentence, path in zip(sentences, paths):
                    if os.path.exists(path) and os.path.getsize(path) > 80:
                        results.append(
                            {
                                "text": sentence,
                                "path": path,
                                "duration": self._get_audio_duration(path),
                            }
                        )
        except RuntimeError as exc:
            print(f"[DubbingSkill] TTS 失败: {exc}")
            return []
        if len(results) < len(sentences):
            raise RuntimeError(
                f"tts_sentence_partial: {len(results)}/{len(sentences)} clip={clip_index}"
            )
        return results

    def _generate_tts(self, text: str, output_path: str):
        """使用 Edge TTS 生成语音（带重试）。"""
        from python_agent.tts_provider import run_async, synthesize_to_file

        cache_dir = self._tts_cache_dir(os.path.dirname(output_path) or ".")
        run_async(
            synthesize_to_file(
                text,
                self.voice,
                output_path,
                cache_dir=cache_dir,
                rate=self.tts_rate,
                pitch=self.tts_pitch,
            )
        )

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频文件时长（秒）"""
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        except Exception:
            return 0.0
