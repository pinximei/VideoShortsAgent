"""
RenderSkill - 视频渲染技能

使用 FFmpeg 从原始视频中裁剪指定片段，生成 ASS 字幕并烧录。

流程：
1. FFmpeg 裁剪视频片段（-ss/-to）
2. 生成 ASS 字幕文件（居中大字、描边、动画）
3. 烧录字幕到视频（-vf ass=）
4. 可选：竖屏适配（9:16）

使用示例：
    skill = RenderSkill()
    output = skill.execute("input.mp4", analysis_result, "./output")
"""
import os
import subprocess


class RenderSkill:
    """视频渲染技能

    使用 FFmpeg 裁剪视频片段并叠加字幕。
    """

    def __init__(self):
        # 检查 FFmpeg 是否可用
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, text=True, timeout=5
            )
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            print(f"[RenderSkill] FFmpeg 已就绪: {version_line} ✓")
        except Exception as e:
            print(f"[RenderSkill] ⚠️ FFmpeg 不可用: {e}")

    def execute(self, video_path: str, analysis: dict, output_dir: str) -> str:
        """执行视频渲染

        Args:
            video_path: 原始视频文件路径
            analysis: AnalysisSkill 返回的分析结果 {start, end, hook_text}
            output_dir: 输出目录

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

        # 中间文件和输出文件
        clip_path = os.path.join(output_dir, "clip_raw.mp4")
        ass_path = os.path.join(output_dir, "subtitle.ass")
        output_path = os.path.join(output_dir, "output_short.mp4")

        # Step 1: 裁剪视频片段
        print(f"[RenderSkill] Step 1/3: 裁剪视频...")
        self._clip_video(video_path, start, end, clip_path)

        # Step 2: 生成 ASS 字幕
        print(f"[RenderSkill] Step 2/3: 生成字幕...")
        self._generate_ass(hook_text, duration, ass_path)

        # Step 3: 烧录字幕
        print(f"[RenderSkill] Step 3/3: 烧录字幕...")
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

    def _clip_video(self, input_path: str, start: float, end: float, output_path: str):
        """FFmpeg 裁剪视频片段"""
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-to", str(end),
            "-i", input_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "fast",
            output_path
        ]
        self._run_ffmpeg(cmd, "裁剪")

    def _generate_ass(self, text: str, duration: float, output_path: str):
        """生成 ASS 字幕文件

        样式：居中大字、黄色描边、半透明底栏、淡入动画
        """
        # 时间格式转换
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

        print(f"[RenderSkill] 字幕文件: {output_path}")

    def _burn_subtitle(self, video_path: str, ass_path: str, output_path: str):
        """将 ASS 字幕烧录到视频"""
        # Windows 路径需要转义
        ass_path_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"ass='{ass_path_escaped}'",
            "-c:v", "libx264",
            "-c:a", "copy",
            "-preset", "fast",
            output_path
        ]
        self._run_ffmpeg(cmd, "烧录字幕")

    def _run_ffmpeg(self, cmd: list, step_name: str):
        """执行 FFmpeg 命令"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                print(f"[RenderSkill] ⚠️ {step_name}警告: {result.stderr[-500:]}")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"FFmpeg {step_name}超时（120秒）")
        except Exception as e:
            raise RuntimeError(f"FFmpeg {step_name}失败: {e}")
