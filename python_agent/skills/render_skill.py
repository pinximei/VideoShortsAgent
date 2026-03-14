"""
RenderSkill - 视频渲染技能

支持两种渲染模式：
- 基础模式：FFmpeg 裁剪 + ASS 字幕烧录
- 特效模式：FFmpeg 裁剪 + Remotion 特效覆盖层 + FFmpeg 合成

流程：
1. FFmpeg 裁剪视频片段
2. (可选) Remotion 渲染特效覆盖层（透明 WebM）
3. FFmpeg 合成最终视频（叠加特效 + 或 ASS 字幕）
"""
import os
import json
import subprocess


# Remotion 项目路径
REMOTION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "remotion_effects")


class RenderSkill:
    """视频渲染技能"""

    def __init__(self):
        # 检查 FFmpeg
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            print(f"[RenderSkill] FFmpeg: {version_line} ✓")
        except Exception as e:
            print(f"[RenderSkill] ⚠️ FFmpeg 不可用: {e}")

        # 检查 Remotion
        self._remotion_available = os.path.exists(os.path.join(REMOTION_DIR, "node_modules"))
        if self._remotion_available:
            print(f"[RenderSkill] Remotion: {REMOTION_DIR} ✓")
        else:
            print(f"[RenderSkill] Remotion: 未安装（将使用 ASS 字幕模式）")

    def execute(self, video_path: str, analysis: dict, output_dir: str,
                effects: dict = None) -> str:
        """执行视频渲染

        Args:
            video_path: 原始视频文件路径
            analysis: {start, end, hook_text}
            output_dir: 输出目录
            effects: 可选特效配置 {"caption_style": "spring", "gradient": True, ...}

        Returns:
            渲染后的视频文件路径
        """
        os.makedirs(output_dir, exist_ok=True)

        start = float(analysis.get("start", 0))
        end = float(analysis.get("end", 0))
        hook_text = analysis.get("hook_text", "")
        duration = end - start

        print(f"[RenderSkill] 裁剪片段: {start}s - {end}s ({duration:.1f}s)")
        print(f"[RenderSkill] 字幕文案: {hook_text}")

        # 文件路径
        clip_path = os.path.join(output_dir, "clip_raw.mp4")
        output_path = os.path.join(output_dir, "output_short.mp4")

        # Step 1: 裁剪视频片段
        print(f"[RenderSkill] Step 1: 裁剪视频...")
        self._clip_video(video_path, start, end, clip_path)

        # Step 2: 选择渲染模式
        use_remotion = effects and self._remotion_available
        if use_remotion:
            print(f"[RenderSkill] Step 2: Remotion 特效渲染...")
            overlay_path = os.path.join(output_dir, "effect_overlay.webm")
            self._render_remotion_overlay(hook_text, duration, effects, overlay_path)

            print(f"[RenderSkill] Step 3: FFmpeg 合成...")
            self._composite_overlay(clip_path, overlay_path, output_path)
        else:
            print(f"[RenderSkill] Step 2: ASS 字幕模式...")
            ass_path = os.path.join(output_dir, "subtitle.ass")
            self._generate_ass(hook_text, duration, ass_path)

            print(f"[RenderSkill] Step 3: 烧录字幕...")
            self._burn_subtitle(clip_path, ass_path, output_path)

        # 清理中间文件
        if os.path.exists(clip_path):
            os.remove(clip_path)

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"[RenderSkill] ✅ 渲染完成: {output_path} ({file_size / 1024:.1f} KB)")
        else:
            print(f"[RenderSkill] ❌ 渲染失败：输出文件不存在")

        return output_path

    # ========== FFmpeg 操作 ==========

    def _clip_video(self, input_path: str, start: float, end: float, output_path: str):
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-to", str(end),
            "-i", input_path, "-c:v", "libx264", "-c:a", "aac",
            "-preset", "fast", output_path
        ]
        self._run_cmd(cmd, "裁剪")

    def _generate_ass(self, text: str, duration: float, output_path: str):
        end_h = int(duration // 3600)
        end_m = int((duration % 3600) // 60)
        end_s = duration % 60

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
Dialogue: 0,0:00:00.00,{end_h}:{end_m:02d}:{end_s:05.2f},Hook,,0,0,0,,{{\\fad(500,300)}}{text}
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

    def _burn_subtitle(self, video_path: str, ass_path: str, output_path: str):
        ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"ass='{ass_escaped}'",
            "-c:v", "libx264", "-c:a", "copy", "-preset", "fast",
            output_path
        ]
        self._run_cmd(cmd, "烧录字幕")

    def _composite_overlay(self, video_path: str, overlay_path: str, output_path: str):
        """将特效覆盖层叠加到视频上"""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", overlay_path,
            "-filter_complex", "[0:v][1:v]overlay=0:0:shortest=1[out]",
            "-map", "[out]", "-map", "0:a?",
            "-c:v", "libx264", "-c:a", "copy", "-preset", "fast",
            output_path
        ]
        self._run_cmd(cmd, "合成特效")

    # ========== Remotion 渲染 ==========

    def _render_remotion_overlay(self, text: str, duration: float, effects: dict, output_path: str):
        """调用 Remotion CLI 渲染特效覆盖层"""
        fps = 30
        frames = int(duration * fps)

        caption_style = effects.get("caption_style", "spring")

        props = json.dumps({
            "text": text,
            "style": caption_style,
        }, ensure_ascii=False)

        cmd = [
            "npx", "remotion", "render",
            "src/index.tsx", "CaptionOverlay",
            "--output", os.path.abspath(output_path),
            f"--props={props}",
            f"--frames=0-{frames - 1}",
            "--codec=vp9",
            "--image-format=png",
        ]

        print(f"[RenderSkill] Remotion: {frames} 帧, style={caption_style}")
        self._run_cmd(cmd, "Remotion 渲染", cwd=REMOTION_DIR, timeout=300)

    # ========== 工具方法 ==========

    def _run_cmd(self, cmd: list, step_name: str, cwd: str = None, timeout: int = 120):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
            if result.returncode != 0:
                stderr = result.stderr[-500:] if result.stderr else ""
                print(f"[RenderSkill] ⚠️ {step_name}警告: {stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{step_name}超时（{timeout}秒）")
        except Exception as e:
            raise RuntimeError(f"{step_name}失败: {e}")
