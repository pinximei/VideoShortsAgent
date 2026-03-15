"""
DubbingSkill - 中文配音技能（句级精确同步）

按句子拆分 tts_text → 逐句生成 TTS → 拼接成完整音频。
返回每句话的精确起止时间，用于字幕精确同步。
"""
import os
import re
import json
import asyncio
import subprocess


VOICE_MALE = "zh-CN-YunxiNeural"
VOICE_FEMALE = "zh-CN-XiaoxiaoNeural"
DEFAULT_VOICE = VOICE_MALE

# 句间停顿（秒）
SENTENCE_PAUSE = 0.2
# 音频无法居中时的最小前置留白（秒）
MIN_LEAD_SILENCE = 0.3
# 前置留白上限（秒）,切换场景后应尽快出声
MAX_LEAD_SILENCE = 0.5


class DubbingSkill:
    """中文配音技能（句级精确同步）"""

    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice
        print(f"[DubbingSkill] 语音: {self.voice} ✓")

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

        clips = analysis.get("clips", [])
        clips_with_tts = [c for c in clips if c.get("tts_text")]

        if not clips_with_tts:
            print("[DubbingSkill] ⚠️ clips 中无 tts_text 字段")
            return {"tts_clips": []}

        print(f"[DubbingSkill] 开始生成 TTS: {len(clips_with_tts)} 个片段")

        tts_clips = []
        for i, clip in enumerate(clips_with_tts):
            tts_text = clip["tts_text"]
            print(f"\n  [片段 {i+1}] {tts_text[:60]}...")

            # 1. 按句拆分
            sentences = self._split_sentences(tts_text)
            print(f"    拆分为 {len(sentences)} 个句子")

            # 2. 并发生成所有句子的 TTS
            sentence_audios = self._generate_tts_batch(sentences, tts_dir, i)
            for j, sa in enumerate(sentence_audios):
                print(f"    [{j+1}] {sa['duration']:.1f}s | {sa['text']}")

            if not sentence_audios:
                continue

            # 3. 拼接所有句子为一个完整音频（居中对齐，前后留白）
            clip_audio_path = os.path.join(tts_dir, f"tts_clip_{i}.mp3")
            video_duration = float(clip.get("end", 0)) - float(clip.get("start", 0))
            sentence_timeline, total_duration = self._concat_sentence_audios(
                sentence_audios, clip_audio_path, tts_dir, i, video_duration
            )

            # 4. 总时长兜底（拼接计算失败时用 ffprobe）
            if total_duration <= 0:
                total_duration = self._get_audio_duration(clip_audio_path)

            # ffprobe 校验（可能返回 0，不用作主要来源）
            probe_duration = self._get_audio_duration(clip_audio_path)
            if probe_duration > 0 and abs(probe_duration - total_duration) > 1.0:
                print(f"    ⚠️ 时长差异: 计算={total_duration:.1f}s, ffprobe={probe_duration:.1f}s")

            tts_clips.append({
                "path": clip_audio_path,
                "duration": total_duration,
                "sentences": sentence_timeline,
                "index": i
            })
            print(f"    → 总时长: {total_duration:.1f}s")

            # 5. 清理句子临时文件
            for sa in sentence_audios:
                if os.path.exists(sa["path"]):
                    os.remove(sa["path"])

        # 恢复原始语音设置
        self.voice = original_voice

        print(f"\n[DubbingSkill] ✅ 完成: {len(tts_clips)} 个 TTS 音频（句级精确计时）")
        return {"tts_clips": tts_clips}

    def _split_sentences(self, text: str) -> list:
        """按标点拆分句子"""
        # 先按句号等拆
        sentences = re.split(r'[。！？；\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # 长句按逗号二次拆分
        result = []
        for s in sentences:
            if len(s) > 20:
                parts = re.split(r'[，,、]+', s)
                parts = [p.strip() for p in parts if p.strip()]
                result.extend(parts)
            else:
                result.append(s)

        return result if result else [text]

    def _concat_sentence_audios(self, sentence_audios: list,
                                 output_path: str, tts_dir: str,
                                 clip_index: int, video_duration: float = 0) -> tuple:
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
        content_duration += SENTENCE_PAUSE * max(0, len(sentence_audios) - 1)

        # 计算前后留白：前留白 ≤ 0.5 秒（快速出声），剩余放尾部
        if video_duration > 0 and video_duration > content_duration:
            total_padding = video_duration - content_duration
            lead_silence = min(total_padding / 2, MAX_LEAD_SILENCE)
            trail_silence = total_padding - lead_silence
            print(f"    留白分配: 视频={video_duration:.1f}s, 语音={content_duration:.1f}s, "
                  f"前={lead_silence:.1f}s, 后={trail_silence:.1f}s")
        else:
            lead_silence = MIN_LEAD_SILENCE
            trail_silence = 0.0

        # 生成静音文件
        silence_path = os.path.join(tts_dir, f"silence_{clip_index}.mp3")
        self._generate_silence(silence_path, SENTENCE_PAUSE)

        lead_silence_path = os.path.join(tts_dir, f"lead_{clip_index}.mp3")
        self._generate_silence(lead_silence_path, lead_silence)

        temp_files = [silence_path, lead_silence_path]

        # 构建拼接列表：前留白 + 句子（句间停顿） + 后留白
        concat_list_path = os.path.join(tts_dir, f"concat_{clip_index}.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f:
            f.write(f"file '{lead_silence_path}'\n")
            for j, sa in enumerate(sentence_audios):
                f.write(f"file '{sa['path']}'\n")
                if j < len(sentence_audios) - 1:
                    f.write(f"file '{silence_path}'\n")
            # 添加尾部留白
            if trail_silence > 0.05:
                trail_silence_path = os.path.join(tts_dir, f"trail_{clip_index}.mp3")
                self._generate_silence(trail_silence_path, trail_silence)
                f.write(f"file '{trail_silence_path}'\n")
                temp_files.append(trail_silence_path)

        temp_files.append(concat_list_path)

        # FFmpeg concat
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path, "-c", "copy", output_path
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except Exception as e:
            print(f"    ⚠️ 拼接失败: {e}")

        # 计算每句的精确时间轴（偏移前留白）
        timeline = []
        current_time = lead_silence
        for j, sa in enumerate(sentence_audios):
            start = current_time
            end = start + sa["duration"]
            timeline.append({
                "text": sa["text"],
                "start": round(start, 3),
                "end": round(end, 3)
            })
            current_time = end + (SENTENCE_PAUSE if j < len(sentence_audios) - 1 else 0)

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

    def _generate_tts_batch(self, sentences: list, tts_dir: str, clip_index: int) -> list:
        """并发生成所有句子的 TTS，返回音频信息列表"""
        import edge_tts

        paths = [os.path.join(tts_dir, f"sent_{clip_index}_{j}.mp3")
                 for j in range(len(sentences))]

        async def _run_all():
            tasks = []
            for text, path in zip(sentences, paths):
                comm = edge_tts.Communicate(text, self.voice)
                tasks.append(comm.save(path))
            await asyncio.gather(*tasks)

        # 兼容已有事件循环
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _run_all())
                future.result(timeout=120)
        else:
            asyncio.run(_run_all())

        # 收集结果
        results = []
        for j, (sentence, path) in enumerate(zip(sentences, paths)):
            if os.path.exists(path):
                duration = self._get_audio_duration(path)
                results.append({"text": sentence, "path": path, "duration": duration})
        return results

    def _generate_tts(self, text: str, output_path: str):
        """使用 edge-tts 生成语音文件"""
        import edge_tts

        async def _run():
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(output_path)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _run())
                future.result(timeout=60)
        else:
            asyncio.run(_run())

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
