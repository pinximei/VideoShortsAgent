"""
SubtitleSkill - 字幕生成与烧录技能

生成 ASS 字幕文件并烧录到视频上。
从 app.py 中的 process_subtitle 函数的字幕相关逻辑抽取而来。
"""
import os
import subprocess


class SubtitleSkill:
    """字幕生成与烧录技能"""

    def generate_ass(self, sentences: list, video_path: str, output_path: str):
        """生成 ASS 字幕文件

        Args:
            sentences: 字幕列表 [{"text": "...", "start": 0.0, "end": 3.5}, ...]
            video_path: 视频文件（用于获取分辨率）
            output_path: ASS 文件输出路径
        """
        # 获取视频宽度
        video_width = self._get_video_width(video_path)
        font_size = 72
        max_chars_per_line = int((video_width - 80) / (font_size * 0.8))
        print(f"[SubtitleSkill] 视频宽度={video_width}px, 每行最多{max_chars_per_line}字")

        # 文本换行 + 去尾部标点
        dialogues = []
        for s in sentences:
            wrapped = self._wrap_text(s["text"], max_chars_per_line)
            final_lines = []
            for line in wrapped.split("\\N"):
                final_lines.append(line.rstrip("，。、；！？,.;!?"))
            wrapped = "\\N".join(final_lines)

            s_t, e_t = s["start"], s["end"]
            s_h, s_m, s_s = int(s_t // 3600), int((s_t % 3600) // 60), s_t % 60
            e_h, e_m, e_s = int(e_t // 3600), int((e_t % 3600) // 60), e_t % 60
            dialogues.append(
                f"Dialogue: 0,{s_h}:{s_m:02d}:{s_s:05.2f},{e_h}:{e_m:02d}:{e_s:05.2f},"
                f"Hook,,0,0,0,,{{\\fad(150,150)}}{wrapped}"
            )

        ass_content = f"""[Script Info]
Title: VideoShortsAgent Subtitle
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Microsoft YaHei,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,4,2,2,40,40,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(dialogues) + "\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
        print(f"[SubtitleSkill] ASS 字幕已生成: {output_path}")

    def burn_subtitle(self, video_path: str, ass_path: str, output_path: str,
                      audio_path: str = None, timeout: int = 600):
        """将字幕烧录到视频上

        Args:
            video_path: 源视频
            ass_path: ASS 字幕文件
            output_path: 输出视频路径
            audio_path: 可选，替换音轨（TTS 配音）
            timeout: 超时秒数
        """
        ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

        if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            # 有配音：去原声 + 加配音 + 加字幕
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-vf", f"subtitles=filename='{ass_escaped}'",
                "-map", "0:v", "-map", "1:a",
                "-c:v", "libx264", "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-preset", "ultrafast",
                "-shortest",
                output_path
            ]
        else:
            # 无配音：只加字幕
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", f"subtitles=filename='{ass_escaped}'",
                "-c:v", "libx264", "-c:a", "copy",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-preset", "ultrafast",
                output_path
            ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                stderr = result.stderr[-500:] if result.stderr else ""
                print(f"[SubtitleSkill] ⚠️ 烧录警告: {stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"字幕烧录超时（{timeout}秒）")

    def _get_video_width(self, video_path: str) -> int:
        """获取视频宽度"""
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-select_streams", "v:0",
                 "-show_entries", "stream=width", "-of", "csv=p=0", video_path],
                capture_output=True, text=True, timeout=10
            )
            return int(r.stdout.strip())
        except Exception:
            return 1920

    def _wrap_text(self, text: str, max_chars: int = 24) -> str:
        """长文本换行"""
        if len(text) <= max_chars:
            return text
        lines = []
        while len(text) > max_chars:
            cut = -1
            for p in ['，', '。', '、', '；', ',', ' ']:
                pos = text.rfind(p, 0, max_chars + 1)
                if pos > 0:
                    cut = pos + 1
                    break
            if cut <= 0:
                for p in ['，', '。', '、', '；', ',', ' ']:
                    pos = text.find(p, max_chars)
                    if pos > 0:
                        cut = pos + 1
                        break
            if cut <= 0:
                if len(text) > max_chars * 1.5:
                    cut = len(text) // 2
                else:
                    break
            lines.append(text[:cut])
            text = text[cut:]
        if text:
            lines.append(text)
        return "\\N".join(lines)
