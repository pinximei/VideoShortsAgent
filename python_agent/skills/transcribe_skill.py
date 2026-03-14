"""
TranscribeSkill - 语音转文字技能

支持两种模式：
- local: 本地 faster-whisper 模型（离线，较慢）
- groq:  Groq Whisper API（在线，极快）

核心设计：
- execute() 接口统一，输出格式一致
- Groq 模式自动提取压缩音频后上传
"""
import os
import json
import subprocess


class TranscribeSkill:
    """语音转文字技能（支持本地/Groq 双模式）"""

    def __init__(self, model_path: str = "base", mode: str = "local",
                 groq_api_key: str = ""):
        """初始化

        Args:
            model_path: 本地 Whisper 模型路径（mode=local 时使用）
            mode: "local" 或 "groq"
            groq_api_key: Groq API Key（mode=groq 时使用）
        """
        self.mode = mode
        self.groq_api_key = groq_api_key
        self._model = None
        self._model_path = model_path

        if mode == "groq":
            if not groq_api_key:
                print(f"[TranscribeSkill] ⚠️ Groq 模式需要 API Key，降级为本地模式")
                self.mode = "local"
                self._load_local_model(model_path)
            else:
                # 预检 groq 模块是否可用
                try:
                    import groq  # noqa: F401
                    print(f"[TranscribeSkill] 模式: Groq API（在线） ✓")
                except ImportError:
                    print(f"[TranscribeSkill] ⚠️ groq 模块未安装，降级为本地模式")
                    print(f"[TranscribeSkill]    请运行: pip install groq")
                    self.mode = "local"
                    self._load_local_model(model_path)
        else:
            print(f"[TranscribeSkill] 模式: 本地 faster-whisper")
            self._load_local_model(model_path)

    def _load_local_model(self, model_path: str):
        from faster_whisper import WhisperModel
        print(f"[TranscribeSkill] 正在加载模型: {model_path}...")
        self._model = WhisperModel(model_path, device="cpu", compute_type="int8")
        print(f"[TranscribeSkill] 模型加载完成 ✓")

    def execute(self, video_path: str, output_dir: str):
        """执行转录

        Returns:
            (transcript_path, detected_language)
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"输入文件不存在: {video_path}")
        os.makedirs(output_dir, exist_ok=True)

        if self.mode == "groq":
            return self._transcribe_groq(video_path, output_dir)
        else:
            return self._transcribe_local(video_path, output_dir)

    def _transcribe_local(self, video_path: str, output_dir: str):
        """本地 faster-whisper 转录"""
        print(f"[TranscribeSkill] 本地转录: {video_path}")
        segments, info = self._model.transcribe(video_path)

        detected_lang = info.language
        lang_prob = info.language_probability
        print(f"[TranscribeSkill] 检测到语言: {detected_lang} (置信度: {lang_prob:.2f})")

        segment_list = []
        for segment in segments:
            segment_list.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip()
            })

        print(f"[TranscribeSkill] 转录完成，共 {len(segment_list)} 个片段")
        return self._save_transcript(output_dir, detected_lang, lang_prob, segment_list)

    def _transcribe_groq(self, video_path: str, output_dir: str):
        """Groq Whisper API 在线转录"""
        from groq import Groq

        # 1. 提取压缩音频（16kHz mono MP3，控制在 25MB 以内）
        audio_path = os.path.join(output_dir, "audio_for_groq.mp3")
        print(f"[TranscribeSkill] 提取压缩音频...")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-ar", "16000", "-ac", "1", "-b:a", "48k",
            audio_path
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        print(f"[TranscribeSkill] 音频大小: {file_size_mb:.1f}MB")

        if file_size_mb > 25:
            print(f"[TranscribeSkill] ⚠️ 音频超过 25MB，尝试更低码率...")
            cmd[-1] = audio_path  # 覆盖
            cmd[cmd.index("48k")] = "24k"
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            print(f"[TranscribeSkill] 重压缩后: {file_size_mb:.1f}MB")

        # 2. 调用 Groq API
        print(f"[TranscribeSkill] 上传到 Groq API...")
        client = Groq(api_key=self.groq_api_key)

        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                file=("audio.mp3", f),
                model="whisper-large-v3",
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )

        # 3. 解析结果
        detected_lang = getattr(response, "language", "unknown")
        print(f"[TranscribeSkill] Groq 转录完成，语言: {detected_lang}")

        segment_list = []
        segments = getattr(response, "segments", [])
        for seg in segments:
            segment_list.append({
                "start": round(seg.get("start", seg.get("start", 0)), 2),
                "end": round(seg.get("end", seg.get("end", 0)), 2),
                "text": seg.get("text", "").strip()
            })

        print(f"[TranscribeSkill] 共 {len(segment_list)} 个片段")

        # 清理临时音频
        if os.path.exists(audio_path):
            os.remove(audio_path)

        return self._save_transcript(output_dir, detected_lang, 1.0, segment_list)

    def _save_transcript(self, output_dir, language, probability, segments):
        """保存转录结果"""
        transcript_data = {
            "language": language,
            "language_probability": round(probability, 4),
            "segments": segments
        }
        output_path = os.path.join(output_dir, "transcript.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)

        print(f"[TranscribeSkill] 已保存: {output_path}")
        return output_path, language
