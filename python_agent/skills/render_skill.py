"""
RenderSkill - 视频渲染技能

支持：
- 单片段模式：裁剪 + 字幕
- 多片段模式：多段裁剪 + 逐段字幕 + FFmpeg concat 拼接
- Remotion 特效（可选）

流程（多片段）：
1. 逐段 FFmpeg 裁剪
2. 逐段 ASS 字幕生成 + 烧录
3. FFmpeg concat 拼接所有片段为最终视频
"""
import os
import json
import subprocess


REMOTION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "remotion_effects")


class RenderSkill:
    """视频渲染技能"""

    def __init__(self):
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            print(f"[RenderSkill] FFmpeg: {version_line} ✓")
        except Exception as e:
            print(f"[RenderSkill] ⚠️ FFmpeg 不可用: {e}")

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
            analysis: 分析结果，支持两种格式：
                - 多片段: {"clips": [{"start": 1.0, "end": 5.0, "hook_text": "..."}, ...]}
                - 单片段: {"start": 1.0, "end": 5.0, "hook_text": "..."}
            output_dir: 输出目录
            effects: 可选特效配置

        Returns:
            渲染后的视频文件路径
        """
        os.makedirs(output_dir, exist_ok=True)

        # 统一为 clips 列表
        clips = analysis.get("clips", [])
        if not clips:
            # 兼容旧的单片段格式
            clips = [{
                "start": float(analysis.get("start", 0)),
                "end": float(analysis.get("end", 0)),
                "hook_text": analysis.get("hook_text", "")
            }]

        output_path = os.path.join(output_dir, "output_short.mp4")

        if len(clips) == 1:
            # 单片段：直接裁剪+字幕
            self._render_single(video_path, clips[0], output_path, output_dir, effects)
        else:
            # 多片段：逐段处理 + concat 拼接
            self._render_multi(video_path, clips, output_path, output_dir, effects)

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"[RenderSkill] ✅ 最终输出: {output_path} ({file_size / 1024:.1f} KB)")
        else:
            print(f"[RenderSkill] ❌ 渲染失败：输出文件不存在")

        return output_path

    def _render_single(self, video_path: str, clip: dict, output_path: str,
                       output_dir: str, effects: dict = None):
        """渲染单个片段"""
        start = float(clip["start"])
        end = float(clip["end"])
        hook_text = clip.get("hook_text", "")
        duration = end - start

        print(f"[RenderSkill] 片段: {start}s - {end}s ({duration:.1f}s)")
        print(f"[RenderSkill] 字幕: {hook_text}")

        clip_path = os.path.join(output_dir, "clip_raw.mp4")
        self._clip_video(video_path, start, end, clip_path)

        ass_path = os.path.join(output_dir, "subtitle.ass")
        self._generate_ass(hook_text, duration, ass_path)
        self._burn_subtitle(clip_path, ass_path, output_path)

        # 清理
        if os.path.exists(clip_path):
            os.remove(clip_path)

    def _render_multi(self, video_path: str, clips: list, output_path: str,
                      output_dir: str, effects: dict = None):
        """渲染多个片段并拼接"""
        print(f"[RenderSkill] 多片段模式: {len(clips)} 个片段")

        segment_paths = []
        for i, clip in enumerate(clips):
            start = float(clip["start"])
            end = float(clip["end"])
            hook_text = clip.get("hook_text", "")
            duration = end - start

            print(f"\n[RenderSkill] --- 片段 {i+1}/{len(clips)} ---")
            print(f"  时间: {start}s - {end}s ({duration:.1f}s)")
            print(f"  字幕: {hook_text}")

            clip_path = os.path.join(output_dir, f"clip_{i}_raw.mp4")
            ass_path = os.path.join(output_dir, f"subtitle_{i}.ass")
            segment_path = os.path.join(output_dir, f"segment_{i}.mp4")

            # 裁剪
            self._clip_video(video_path, start, end, clip_path)

            # 字幕
            self._generate_ass(hook_text, duration, ass_path)
            self._burn_subtitle(clip_path, ass_path, segment_path)

            segment_paths.append(segment_path)

            # 清理中间文件
            if os.path.exists(clip_path):
                os.remove(clip_path)

        print(f"\n[RenderSkill] 拼接 {len(segment_paths)} 个片段...")
        self._concat_videos(segment_paths, output_path, output_dir, effects)

        # 清理片段文件
        for path in segment_paths:
            if os.path.exists(path):
                os.remove(path)

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

    def _concat_videos(self, video_paths: list, output_path: str, output_dir: str,
                        effects: dict = None):
        """FFmpeg xfade 拼接多个视频（交叉淡入淡出转场）"""
        if len(video_paths) == 1:
            import shutil
            shutil.copy2(video_paths[0], output_path)
            return

        # 从 effects 读取转场配置
        transition = "fade"  # 默认
        transition_duration = 0.5
        if effects:
            transition = effects.get("transition", "fade")
            transition_duration = float(effects.get("transition_duration", 0.5))

        # 验证转场类型
        valid_transitions = [
            "fade", "wipeleft", "wiperight", "wipeup", "wipedown",
            "slideup", "slidedown", "slideleft", "slideright",
            "circleopen", "circleclose", "dissolve", "pixelize",
            "diagtl", "diagtr", "diagbl", "diagbr",
        ]
        if transition not in valid_transitions:
            print(f"[RenderSkill] ⚠️ 未知转场 '{transition}'，使用 fade")
            transition = "fade"

        print(f"[RenderSkill] 转场: {transition} ({transition_duration}s)")

        # 获取每个片段的时长
        durations = []
        for path in video_paths:
            dur = self._get_duration(path)
            durations.append(dur)
            print(f"  片段时长: {path} = {dur:.2f}s")

        # 构建 xfade 滤镜链
        # 2个片段: [0:v][1:v]xfade=transition=fade:duration=0.5:offset=T
        # 3个片段: 先合前2个，再合第3个
        inputs = []
        for path in video_paths:
            inputs.extend(["-i", path])

        # 计算每个转场的 offset（前面所有片段时长之和 - 转场时长累积）
        filter_parts = []
        offsets = []
        cumulative = 0
        for i in range(len(durations) - 1):
            cumulative += durations[i]
            offset = cumulative - transition_duration * (i + 1)
            offsets.append(max(0, offset))

        # 视频滤镜链
        if len(video_paths) == 2:
            filter_parts.append(
                f"[0:v][1:v]xfade=transition={transition}:duration={transition_duration}:offset={offsets[0]:.3f}[vout]"
            )
            filter_parts.append(
                f"[0:a][1:a]acrossfade=d={transition_duration}[aout]"
            )
            map_args = ["-map", "[vout]", "-map", "[aout]"]
        else:
            # 多个片段：链式 xfade
            v_prev = "[0:v]"
            a_prev = "[0:a]"
            for i in range(len(video_paths) - 1):
                v_out = "[vout]" if i == len(video_paths) - 2 else f"[v{i}]"
                a_out = "[aout]" if i == len(video_paths) - 2 else f"[a{i}]"
                filter_parts.append(
                    f"{v_prev}[{i+1}:v]xfade=transition={transition}:duration={transition_duration}:offset={offsets[i]:.3f}{v_out}"
                )
                filter_parts.append(
                    f"{a_prev}[{i+1}:a]acrossfade=d={transition_duration}{a_out}"
                )
                v_prev = v_out
                a_prev = a_out
            map_args = ["-map", "[vout]", "-map", "[aout]"]

        filter_complex = ";".join(filter_parts)
        print(f"  转场滤镜: {filter_complex[:200]}...")

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_complex
        ] + map_args + [
            "-c:v", "libx264", "-c:a", "aac", "-preset", "fast",
            output_path
        ]
        self._run_cmd(cmd, "转场拼接")

    def _get_duration(self, video_path: str) -> float:
        """获取视频时长"""
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        except Exception:
            return 5.0  # 默认 5 秒

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
