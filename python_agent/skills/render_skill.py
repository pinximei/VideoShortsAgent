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
_VALID_X264_PRESETS = frozenset(
    {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"},
)


def _clip_bullets(clip: dict) -> list[str]:
    from python_agent.capabilities.clip_text import clip_bullets

    return clip_bullets(clip)


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

    def _x264_preset(self, effects: dict | None) -> str:
        p = str((effects or {}).get("ffmpeg_preset") or "medium")
        return p if p in _VALID_X264_PRESETS else "medium"

    def _apply_bullet_overlay(
        self,
        segment_path: str,
        clip: dict,
        duration: float,
        output_dir: str,
        clip_index: int,
        *,
        effects: dict | None = None,
    ) -> None:
        if not (effects or {}).get("content_highlight"):
            return
        bullets = _clip_bullets(clip)
        if not bullets:
            return
        ass_path = os.path.join(output_dir, f"bullets_{clip_index}.ass")
        self._generate_ass("", duration, ass_path, bullets=bullets)
        tmp = segment_path + ".bul.mp4"
        self._burn_subtitle(
            segment_path, ass_path, tmp, x264_preset=self._x264_preset(effects)
        )
        if os.path.isfile(tmp) and os.path.getsize(tmp) > 1024:
            os.replace(tmp, segment_path)
        if os.path.isfile(ass_path):
            os.remove(ass_path)

    def execute(self, video_path: str, analysis: dict, output_dir: str,
                effects: dict = None, tts_info: dict = None) -> str:
        """执行视频渲染

        Args:
            video_path: 原始视频文件路径
            analysis: 分析结果，clips 列表
            output_dir: 输出目录
            effects: 可选特效配置
            tts_info: dubbing 返回的 TTS 信息（可选）
                {"tts_clips": [{"path": "tts_0.mp3", "duration": 5.2}, ...]}

        Returns:
            渲染后的视频文件路径
        """
        os.makedirs(output_dir, exist_ok=True)

        clips = analysis.get("clips", [])
        if not clips:
            clips = [{
                "start": float(analysis.get("start", 0)),
                "end": float(analysis.get("end", 0)),
                "hook_text": analysis.get("hook_text", "")
            }]

        # 获取 TTS 片段信息
        tts_clips = []
        if tts_info:
            tts_clips = tts_info.get("tts_clips", [])

        output_path = os.path.join(output_dir, "output_short.mp4")

        if len(clips) == 1:
            self._render_single(video_path, clips[0], output_path, output_dir,
                                effects, tts_clips[0] if tts_clips else None)
        else:
            self._render_multi(video_path, clips, output_path, output_dir,
                               effects, tts_clips)

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"[RenderSkill] ✅ 最终输出: {output_path} ({file_size / 1024:.1f} KB)")
        else:
            print(f"[RenderSkill] ❌ 渲染失败：输出文件不存在")

        return output_path

    def _render_single(self, video_path: str, clip: dict, output_path: str,
                       output_dir: str, effects: dict = None, tts_clip: dict = None):
        """渲染单个片段"""
        start = float(clip["start"])
        end = float(clip["end"])
        subtitle_text = clip.get("tts_text", "") or clip.get("hook_text", "")
        video_duration = end - start

        # TTS 时长为主时钟：视频裁剪成与 TTS 一样长
        if tts_clip:
            target_duration = tts_clip["duration"]
            tts_path = tts_clip["path"]
            silent = True
            # 统一调整 end，让视频 = TTS 时长
            end = start + target_duration
            video_duration = target_duration
        else:
            target_duration = video_duration
            tts_path = None
            silent = False

        print(f"[RenderSkill] 片段: {start:.1f}s - {end:.1f}s ({target_duration:.1f}s)")

        clip_path = os.path.join(output_dir, "clip_raw.mp4")
        self._clip_video(
            video_path, start, end, clip_path, silent=silent,
            x264_preset=self._x264_preset(effects),
        )

        # 附加 TTS 音频
        if tts_path:
            with_audio_path = os.path.join(output_dir, "clip_audio.mp4")
            self._attach_audio(clip_path, tts_path, with_audio_path)
            os.replace(with_audio_path, clip_path)

        # 字幕/特效
        sentences = tts_clip.get("sentences") if tts_clip else None
        use_remotion = (effects or {}).get("use_remotion", True) and self._remotion_available
        caption_style = (effects or {}).get("caption_style", "spring")

        if use_remotion:
            # Remotion 特效覆盖层
            self._apply_remotion_caption(
                clip_path, subtitle_text, target_duration, output_path,
                output_dir, caption_style, sentences=sentences, effects=effects
            )
        else:
            # ASS 字幕烧录
            ass_path = os.path.join(output_dir, "subtitle.ass")
            self._generate_ass(
                subtitle_text, target_duration, ass_path,
                sentences=sentences, caption_style=caption_style,
            )
            self._burn_subtitle(
                clip_path, ass_path, output_path, x264_preset=self._x264_preset(effects)
            )

        self._apply_bullet_overlay(
            output_path, clip, target_duration, output_dir, 0, effects=effects
        )

        if os.path.exists(clip_path):
            os.remove(clip_path)

    def _render_multi(self, video_path: str, clips: list, output_path: str,
                      output_dir: str, effects: dict = None, tts_clips: list = None):
        """渲染多个片段并拼接"""
        from python_agent.config import get_config
        MAX_TOTAL_DURATION = get_config().max_video_duration
        print(f"[RenderSkill] 多片段模式: {len(clips)} 个片段"
              f"{f', {len(tts_clips)} 个 TTS' if tts_clips else ''}")

        # 清理旧的中间文件（避免上次残留文件干扰）
        import glob
        for pattern in ["segment_*.mp4", "clip_*_raw.mp4", "clip_*_audio.mp4",
                        "caption_overlay_*.webm", "gradient_overlay_*.webm", "subtitle_*.ass"]:
            for old_file in glob.glob(os.path.join(output_dir, pattern)):
                os.remove(old_file)

        # 硬限制：总时长截断
        cumulative_duration = 0.0
        valid_clip_count = len(clips)
        for i, clip in enumerate(clips):
            tts_clip = tts_clips[i] if tts_clips and i < len(tts_clips) else None
            dur = tts_clip["duration"] if tts_clip else (float(clip["end"]) - float(clip["start"]))
            cumulative_duration += dur
            if cumulative_duration > MAX_TOTAL_DURATION:
                valid_clip_count = i
                print(f"[RenderSkill] ⚠️ 总时长 {cumulative_duration:.0f}s 超限，只保留前 {i} 个片段")
                break
        clips = clips[:valid_clip_count]
        if tts_clips:
            tts_clips = tts_clips[:valid_clip_count]

        segment_paths = []
        for i, clip in enumerate(clips):
            start = float(clip["start"])
            end = float(clip["end"])
            subtitle_text = clip.get("tts_text", "") or clip.get("hook_text", "")
            video_duration = end - start

            # TTS 时长为主时钟：视频裁剪成与 TTS 一样长
            tts_clip = tts_clips[i] if tts_clips and i < len(tts_clips) else None
            if tts_clip:
                target_duration = tts_clip["duration"]
                tts_path = tts_clip["path"]
                silent = True
                end = start + target_duration
                video_duration = target_duration
            else:
                target_duration = video_duration
                tts_path = None
                silent = False

            print(f"\n[RenderSkill] --- 片段 {i+1}/{len(clips)} ---")
            print(f"  画面: {start:.1f}s - {end:.1f}s ({target_duration:.1f}s)")
            print(f"  字幕: {subtitle_text[:50]}")

            clip_path = os.path.join(output_dir, f"clip_{i}_raw.mp4")
            ass_path = os.path.join(output_dir, f"subtitle_{i}.ass")
            segment_path = os.path.join(output_dir, f"segment_{i}.mp4")

            # 裁剪（静音）
            self._clip_video(
                video_path, start, end, clip_path, silent=silent,
                x264_preset=self._x264_preset(effects),
            )

            # 裁剪结果检查
            if not os.path.exists(clip_path) or os.path.getsize(clip_path) < 1024:
                print(f"  ⚠️ 片段 {i+1} 裁剪失败或文件过小，跳过")
                continue

            # 附加 TTS 音频
            if tts_path and os.path.exists(tts_path):
                with_audio_path = os.path.join(output_dir, f"clip_{i}_audio.mp4")
                self._attach_audio(clip_path, tts_path, with_audio_path)
                if os.path.exists(with_audio_path):
                    os.replace(with_audio_path, clip_path)
                else:
                    print(f"  ⚠️ 附加音频失败，使用静音视频继续")

            # 字幕/特效（每段独立选择）
            sentences = tts_clip.get("sentences") if tts_clip else None
            use_remotion = (effects or {}).get("use_remotion", True) and self._remotion_available
            # 优先使用 clip 级别的 caption_style，降级到全局 effects
            caption_style = clip.get("caption_style") or (effects or {}).get("caption_style", "spring")

            if use_remotion:
                self._apply_remotion_caption(
                    clip_path, subtitle_text, target_duration, segment_path,
                    output_dir, caption_style, sentences=sentences, effects=effects,
                    clip_index=i
                )
            else:
                ass_path = os.path.join(output_dir, f"subtitle_{i}.ass")
                self._generate_ass(
                    subtitle_text, target_duration, ass_path,
                    sentences=sentences, caption_style=caption_style,
                )
                self._burn_subtitle(
                    clip_path, ass_path, segment_path, x264_preset=self._x264_preset(effects)
                )

            self._apply_bullet_overlay(
                segment_path, clip, target_duration, output_dir, i, effects=effects
            )

            if os.path.isfile(segment_path) and os.path.getsize(segment_path) > 1024:
                segment_paths.append(segment_path)
            else:
                print(f"  ⚠️ 片段 {i+1} 输出无效，跳过")

            if os.path.exists(clip_path):
                os.remove(clip_path)

        width, height = self._get_video_resolution(video_path)
        bookend_prefix: list[str] = []
        bookend_suffix: list[str] = []
        remotion_on = (effects or {}).get("use_remotion", True) and self._remotion_available
        if remotion_on:
            colors = (effects or {}).get("gradient_colors") or ["#667eea", "#764ba2"]
            if not isinstance(colors, list) or len(colors) < 2:
                colors = ["#0f0c29", "#302b63"]
            cap = (effects or {}).get("caption_style", "spring")
            if (effects or {}).get("intro_card"):
                intro_path = os.path.join(output_dir, "segment_intro.mp4")
                intro_props: dict = {
                        "heading": str((effects or {}).get("intro_heading") or "")[:80],
                        "subheading": str((effects or {}).get("intro_subheading") or "")[:80],
                        "captionStyle": cap,
                        "colors": colors,
                        "accentColor": colors[0],
                        "layoutStyle": "split-left" if (effects or {}).get("intro_image_path") else "center",
                    }
                if (effects or {}).get("intro_image_path"):
                    intro_props["imagePath"] = effects["intro_image_path"]
                self._render_remotion_composition_mp4(
                    "TitleCard",
                    intro_props,
                    intro_path,
                    output_dir,
                    tag="intro",
                    duration_sec=2.2,
                    width=width,
                    height=height,
                )
                if os.path.isfile(intro_path):
                    bookend_prefix.append(intro_path)
            if (effects or {}).get("outro_card"):
                outro_path = os.path.join(output_dir, "segment_outro.mp4")
                self._render_remotion_composition_mp4(
                    "CTACard",
                    {
                        "heading": "",
                        "ctaText": str((effects or {}).get("outro_cta") or "关注我")[:60],
                        "captionStyle": cap,
                        "colors": list(reversed(colors)),
                        "accentColor": colors[1] if len(colors) > 1 else colors[0],
                    },
                    outro_path,
                    output_dir,
                    tag="outro",
                    duration_sec=2.0,
                    width=width,
                    height=height,
                )
                if os.path.isfile(outro_path):
                    bookend_suffix.append(outro_path)

        if not segment_paths:
            raise RuntimeError("所有片段渲染失败，请检查 B-roll 时长与分镜 start/end")

        all_segments = bookend_prefix + segment_paths + bookend_suffix
        print(f"\n[RenderSkill] 拼接 {len(all_segments)} 个片段（含片头/片尾 {len(bookend_prefix)+len(bookend_suffix)}）...")
        self._concat_videos(
            all_segments, output_path, output_dir, effects, clips=clips,
            x264_preset=self._x264_preset(effects),
        )

        for path in segment_paths:
            if os.path.exists(path):
                os.remove(path)

    # ========== FFmpeg 操作 ==========

    def _clip_video(self, input_path: str, start: float, end: float,
                    output_path: str, silent: bool = False, pad_duration: float = 0,
                    *, x264_preset: str = "medium"):
        """FFmpeg 裁剪视频

        Args:
            silent: 是否静音（去掉原始音轨，用于后续附加 TTS 音频）
            pad_duration: 冻结末帧延长的秒数
        """
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-to", str(end),
            "-i", input_path,
        ]
        if silent:
            cmd += ["-an"]  # 去掉音轨
        else:
            cmd += ["-c:a", "aac", "-b:a", "192k"]
        cmd += [
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", "-profile:v", "high", "-level", "4.1",
            "-movflags", "+faststart", "-preset", x264_preset,
            output_path
        ]
        self._run_cmd(cmd, "裁剪")

        # 冻结末帧延长
        if pad_duration > 0.5 and os.path.exists(output_path):
            padded_path = output_path + ".padded.mp4"
            vf = f"tpad=stop_mode=clone:stop_duration={pad_duration:.3f}"
            pad_cmd = [
                "ffmpeg", "-y", "-i", output_path,
                "-vf", vf,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "18", "-profile:v", "high", "-level", "4.1",
                "-movflags", "+faststart", "-preset", x264_preset,
            ]
            if not silent:
                pad_cmd += ["-af", f"apad=pad_dur={pad_duration:.3f}", "-c:a", "aac", "-b:a", "192k"]
            else:
                pad_cmd += ["-an"]
            pad_cmd.append(padded_path)
            self._run_cmd(pad_cmd, "冻结延长")
            if os.path.exists(padded_path):
                os.replace(padded_path, output_path)

    def _attach_audio(self, video_path: str, audio_path: str, output_path: str):
        """将 TTS 音频附加到静音视频上"""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v", "-map", "1:a",
            "-movflags", "+faststart",
            "-shortest",
            output_path
        ]
        self._run_cmd(cmd, "附加音频")

    def _ass_effect_tags(self, caption_style: str = "spring") -> str:
        style = (caption_style or "spring").strip().lower()
        if style == "fade":
            return r"{\fad(500,400)}{\blur1}"
        if style == "typewriter":
            return r"{\fad(120,80)}"
        return r"{\fad(300,250)}{\blur1}"

    def _generate_ass(self, text: str, duration: float, output_path: str,
                      sentences: list = None, bullets: list | None = None,
                      caption_style: str = "spring"):
        """生成 ASS 字幕文件

        Args:
            sentences: TTS 返回的精确句级时间轴 [{text, start, end}, ...]
                       有此参数时使用精确时间，否则按字数估算
        """
        import re

        tags = self._ass_effect_tags(caption_style)
        dialogues: list[str] = []
        if sentences:
            for s in sentences:
                s_t = s["start"]
                e_t = s["end"]
                s_h, s_m, s_s = int(s_t // 3600), int((s_t % 3600) // 60), s_t % 60
                e_h, e_m, e_s = int(e_t // 3600), int((e_t % 3600) // 60), e_t % 60
                dialogues.append(
                    f"Dialogue: 0,{s_h}:{s_m:02d}:{s_s:05.2f},{e_h}:{e_m:02d}:{e_s:05.2f},"
                    f"Hook,,0,0,0,,{tags}{s['text']}"
                )
        elif (text or "").strip():
            sents = re.split(r'[。！？；\n]+', text)
            sents = [s.strip() for s in sents if s.strip()]
            final = []
            for s in sents:
                if len(s) > 20:
                    parts = re.split(r'[，,、]+', s)
                    final.extend([p.strip() for p in parts if p.strip()])
                else:
                    final.append(s)
            if not final:
                final = [text]

            pause = 0.15
            total_pause = pause * (len(final) - 1) if len(final) > 1 else 0
            available = duration - total_pause
            if available < len(final) * 0.5:
                available = duration
                pause = 0

            char_counts = [len(s) for s in final]
            total_chars = sum(char_counts) or 1
            time_per = [(c / total_chars) * available for c in char_counts]

            current = 0.0
            for s_text, seg_dur in zip(final, time_per):
                seg_dur = max(seg_dur, 0.5)
                s_t = current
                e_t = min(s_t + seg_dur, duration)
                s_h, s_m, s_s = int(s_t // 3600), int((s_t % 3600) // 60), s_t % 60
                e_h, e_m, e_s = int(e_t // 3600), int((e_t % 3600) // 60), e_t % 60
                dialogues.append(
                    f"Dialogue: 0,{s_h}:{s_m:02d}:{s_s:05.2f},{e_h}:{e_m:02d}:{e_s:05.2f},"
                    f"Hook,,0,0,0,,{tags}{s_text}"
                )
                current = e_t + pause

        if bullets:
            n = len(bullets)
            slot = max(0.9, (duration - 0.5) / max(n, 1))
            for i, b_text in enumerate(bullets):
                s_t = 0.35 + i * slot
                e_t = min(s_t + slot * 0.85, max(duration - 0.15, s_t + 0.5))
                s_h, s_m, s_s = int(s_t // 3600), int((s_t % 3600) // 60), s_t % 60
                e_h, e_m, e_s = int(e_t // 3600), int((e_t % 3600) // 60), e_t % 60
                dialogues.append(
                    f"Dialogue: 0,{s_h}:{s_m:02d}:{s_s:05.2f},{e_h}:{e_m:02d}:{e_s:05.2f},"
                    f"Bullet,,0,0,0,,{{\\fad(200,150)}}{b_text}"
                )

        ass_content = f"""[Script Info]
Title: VideoShortsAgent Subtitle
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Microsoft YaHei,64,&H00FFFFFF,&H000000FF,&H00000000,&HC0000000,-1,0,0,0,100,100,3,0,1,3,3,2,40,40,80,1
Style: Bullet,Microsoft YaHei,42,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,2,2,2,60,60,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(dialogues) + "\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

    def _burn_subtitle(self, video_path: str, ass_path: str, output_path: str,
                       *, x264_preset: str = "medium"):
        # Windows 路径处理：反斜杠→正斜杠，冒号用 \: 转义（FFmpeg filtergraph 语法）
        ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"subtitles=filename='{ass_escaped}'",
            "-c:v", "libx264", "-c:a", "copy",
            "-pix_fmt", "yuv420p",
            "-crf", "18", "-profile:v", "high", "-level", "4.1",
            "-movflags", "+faststart",
            "-preset", x264_preset,
            output_path
        ]
        self._run_cmd(cmd, "烧录字幕", timeout=600)

    # ========== Remotion 特效 ==========

    def _apply_remotion_caption(self, video_path: str, text: str, duration: float,
                                output_path: str, output_dir: str, caption_style: str = "spring",
                                sentences: list = None, effects: dict = None, clip_index: int = 0):
        """使用 Remotion 渲染字幕特效覆盖层并叠加到视频上

        流程：
        1. 获取视频分辨率
        2. Remotion 渲染透明字幕覆盖层（WebM/VP9）
        3. 可选：渲染渐变背景覆盖层
        4. FFmpeg 将覆盖层叠加到视频上
        """
        width, height = self._get_video_resolution(video_path)
        fps = 30
        total_frames = max(1, int(duration * fps))

        print(f"[RenderSkill] Remotion 特效: {width}x{height}, {total_frames} 帧, style={caption_style}")

        # 1. 渲染字幕覆盖层
        props = {
            "style": caption_style,
            "durationSec": float(duration),
            "fps": fps,
        }
        if sentences and len(sentences) > 0:
            # DubbingSkill 句级时间轴（秒）→ Remotion 按 currentTime 逐句显示，与 TTS 对齐
            props["sentences"] = sentences
        else:
            props["text"] = text

        caption_overlay_path = os.path.join(output_dir, f"caption_overlay_{clip_index}.webm")
        self._render_remotion_overlay(
            composition="CaptionOverlay",
            props=props,
            output_path=caption_overlay_path,
            width=width, height=height, fps=fps, frames=total_frames,
            output_dir=output_dir, tag=f"caption_{clip_index}"
        )

        if not os.path.exists(caption_overlay_path):
            print(f"[RenderSkill] ⚠️ Remotion 渲染失败，降级为 ASS 字幕")
            ass_path = os.path.join(output_dir, f"subtitle_{clip_index}.ass")
            self._generate_ass(text, duration, ass_path, sentences=sentences)
            self._burn_subtitle(video_path, ass_path, output_path)
            return

        # 2. 可选：渲染渐变背景覆盖层
        gradient_overlay_path = None
        if effects and effects.get("gradient", False):
            colors = effects.get("gradient_colors", ["#FF6B6B", "#4ECDC4"])
            gradient_overlay_path = os.path.join(output_dir, f"gradient_overlay_{clip_index}.webm")
            self._render_remotion_overlay(
                composition="GradientBackground",
                props={"colorFrom": colors[0], "colorTo": colors[1], "opacity": 0.3},
                output_path=gradient_overlay_path,
                width=width, height=height, fps=fps, frames=total_frames,
                output_dir=output_dir, tag=f"gradient_{clip_index}"
            )

        # 3. 叠加覆盖层到视频
        overlays = [caption_overlay_path]
        if gradient_overlay_path and os.path.exists(gradient_overlay_path):
            overlays.insert(0, gradient_overlay_path)  # 渐变在字幕下方

        self._overlay_videos(video_path, overlays, output_path)

        # overlay 失败时降级：直接拷贝原视频
        if not os.path.exists(output_path):
            print(f"[RenderSkill] ⚠️ 覆盖层叠加失败，降级为 ASS 字幕")
            ass_path = os.path.join(output_dir, f"subtitle_fallback_{clip_index}.ass")
            self._generate_ass(text, duration, ass_path, sentences=sentences)
            self._burn_subtitle(video_path, ass_path, output_path)

        # 清理临时覆盖层
        for p in [caption_overlay_path, gradient_overlay_path]:
            if p and os.path.exists(p):
                os.remove(p)

    def _render_remotion_composition_mp4(
        self,
        composition: str,
        props: dict,
        output_path: str,
        output_dir: str,
        *,
        tag: str = "card",
        duration_sec: float = 2.5,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
    ) -> None:
        """渲染 TitleCard / CTACard 等为独立 MP4（片头片尾）。"""
        frames = max(1, int(duration_sec * fps))
        props_path = os.path.abspath(os.path.join(output_dir, f"remotion_props_{tag}.json"))
        with open(props_path, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False)
        props_path_fwd = props_path.replace("\\", "/")
        out_fwd = os.path.abspath(output_path).replace("\\", "/")
        cmd = [
            "npx", "remotion", "render", "src/index.tsx", composition,
            f"--output={out_fwd}",
            f"--props={props_path_fwd}",
            f"--width={width}", f"--height={height}",
            f"--frames=0-{frames - 1}",
        ]
        print(f"[RenderSkill] Remotion 卡片: {composition} ({duration_sec:.1f}s)")
        self._run_cmd(cmd, f"Remotion:{composition}", cwd=REMOTION_DIR, timeout=900, shell=True)

    def _render_remotion_overlay(self, composition: str, props: dict, output_path: str,
                                 width: int, height: int, fps: int, frames: int,
                                 output_dir: str, tag: str = "overlay"):
        """调用 Remotion CLI 渲染透明覆盖层；优先直出 WebM，失败再 PNG 序列。"""
        props_path = os.path.abspath(os.path.join(output_dir, f"remotion_props_{tag}.json"))
        with open(props_path, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False)

        props_path_fwd = props_path.replace("\\", "/")
        out_target = output_path
        if output_path.endswith(".webm"):
            out_target = output_path.replace(".webm", ".mov")
        out_fwd = os.path.abspath(out_target).replace("\\", "/")

        fast_cmd = [
            "npx", "remotion", "render", "src/index.tsx", composition,
            f"--output={out_fwd}",
            f"--props={props_path_fwd}",
            "--codec=vp8",
            "--pixel-format=yuva420p",
            f"--width={width}", f"--height={height}",
            f"--frames=0-{frames - 1}",
        ]
        try:
            self._run_cmd(fast_cmd, f"Remotion:{composition}:fast", cwd=REMOTION_DIR,
                          timeout=420, shell=True)
            if os.path.isfile(out_target) and os.path.getsize(out_target) > 200:
                if output_path != out_target and output_path.endswith(".webm"):
                    os.replace(out_target, output_path)
                if os.path.exists(props_path):
                    os.remove(props_path)
                return
        except Exception:
            pass

        # 降级：PNG 序列帧（兼容旧 Remotion / 直出失败）
        seq_dir = os.path.join(output_dir, f"remotion_seq_{tag}")
        os.makedirs(seq_dir, exist_ok=True)
        seq_dir_fwd = os.path.abspath(seq_dir).replace("\\", "/")

        cmd = [
            "npx", "remotion", "render", "src/index.tsx", composition,
            f"--output={seq_dir_fwd}",
            f"--props={props_path_fwd}",
            "--image-format=png", "--sequence",
            f"--width={width}", f"--height={height}",
            f"--frames=0-{frames - 1}",
        ]
        print(f"[RenderSkill] Remotion 渲染: {composition} ({frames} 帧)")
        self._run_cmd(cmd, f"Remotion:{composition}", cwd=REMOTION_DIR,
                      timeout=600, shell=True)

        # PNG 序列帧 → 带 alpha 的视频（mov+png codec，完整保留透明度）
        # 查找实际帧文件名模式
        import glob
        png_files = sorted(glob.glob(os.path.join(seq_dir, "*.png")))
        if png_files:
            # Remotion 输出格式为 element-0.png, element-1.png... 或 frame0.png...
            first = os.path.basename(png_files[0])
            # 提取模式
            import re
            m = re.match(r"(.+?)(\d+)(\.png)$", first)
            if m:
                prefix = m.group(1)
                num_len = len(m.group(2))
                pattern_fwd = os.path.join(seq_dir, f"{prefix}%0{num_len}d.png").replace("\\", "/")
            else:
                pattern_fwd = os.path.join(seq_dir, "%d.png").replace("\\", "/")

            # 合成为 mov+png（保留 alpha 通道）
            merge_cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", pattern_fwd,
                "-c:v", "png",
                "-pix_fmt", "rgba",
                output_path
            ]
            # 输出改为 .mov 以支持 PNG codec
            if output_path.endswith(".webm"):
                output_path_mov = output_path.replace(".webm", ".mov")
            else:
                output_path_mov = output_path + ".mov"
            merge_cmd[-1] = output_path_mov
            self._run_cmd(merge_cmd, "合成覆盖层")

            # 记录实际路径（覆盖调用者的路径）
            if os.path.exists(output_path_mov):
                if output_path != output_path_mov:
                    os.replace(output_path_mov, output_path)

        # 清理
        import shutil
        if os.path.exists(seq_dir):
            shutil.rmtree(seq_dir, ignore_errors=True)
        if os.path.exists(props_path):
            os.remove(props_path)

    def _overlay_videos(self, base_path: str, overlay_paths: list, output_path: str):
        """将多个透明覆盖层叠加到基础视频上"""
        inputs = ["-i", base_path]
        for p in overlay_paths:
            inputs += ["-i", p]

        # 构建 filter_complex：逐层叠加
        if len(overlay_paths) == 1:
            filter_complex = "[0:v][1:v]overlay=0:0:shortest=1[vout]"
        else:
            # 多层叠加
            parts = []
            prev = "[0:v]"
            for i in range(len(overlay_paths)):
                out = "[vout]" if i == len(overlay_paths) - 1 else f"[tmp{i}]"
                parts.append(f"{prev}[{i+1}:v]overlay=0:0:shortest=1{out}")
                prev = out
            filter_complex = ";".join(parts)

        cmd = [
            "ffmpeg", "-y",
        ] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "0:a?",
            "-c:v", "libx264", "-c:a", "copy",
            "-pix_fmt", "yuv420p",
            "-crf", "18", "-profile:v", "high", "-level", "4.1",
            "-movflags", "+faststart",
            "-preset", "medium",
            output_path
        ]
        self._run_cmd(cmd, "叠加覆盖层")

    def _get_video_resolution(self, video_path: str) -> tuple:
        """获取视频分辨率，返回 (width, height)"""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            video_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            parts = result.stdout.strip().split("x")
            return int(parts[0]), int(parts[1])
        except Exception:
            return 1080, 1920  # 默认竖屏

    def _concat_videos(self, video_paths: list, output_path: str, output_dir: str,
                        effects: dict = None, clips: list = None, *,
                        x264_preset: str = "medium"):
        """FFmpeg xfade 拼接多个视频（支持每段不同转场效果）"""
        if len(video_paths) == 1:
            import shutil
            shutil.copy2(video_paths[0], output_path)
            return

        # 全局默认转场
        default_transition = (effects or {}).get("transition", "fade")
        transition_duration = float((effects or {}).get("transition_duration", 0.25))

        from python_agent.capabilities.registry import VALID_TRANSITIONS, resolve_transition

        valid_transitions = list(VALID_TRANSITIONS)

        # 检测 FFmpeg 是否支持 easing 参数（FFmpeg 7.0+）
        easing_supported = self._check_ffmpeg_easing_support()

        # 为每个转场点确定转场类型（从 clip 级别读取，降级到全局默认）
        transitions = []
        for i in range(len(video_paths) - 1):
            t = default_transition
            if clips and i < len(clips):
                t = clips[i].get("transition_to_next", "") or default_transition
            t = resolve_transition(t, default="fade")
            if t not in valid_transitions:
                t = "fade"
            transitions.append(t)
        print(f"[RenderSkill] 转场序列: {transitions} ({transition_duration}s, easing={'on' if easing_supported else 'off'})")

        # 获取每个片段的时长
        durations = [self._get_duration(path) for path in video_paths]

        # 构建 xfade 滤镜链
        inputs = []
        for path in video_paths:
            inputs.extend(["-i", path])

        # 计算每个转场的 offset
        filter_parts = []
        offsets = []
        cumulative = 0
        for i in range(len(durations) - 1):
            cumulative += durations[i]
            offset = cumulative - transition_duration * (i + 1)
            offsets.append(max(0, offset))

        # 检测片段是否有音频流
        has_audio = False
        try:
            probe_cmd = ["ffprobe", "-v", "quiet", "-select_streams", "a",
                         "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                         video_paths[0]]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
            has_audio = "audio" in probe_result.stdout
        except Exception:
            pass

        # 视频/音频滤镜链（每段用独立转场）
        easing_param = ":easing=easeInOutCubic" if easing_supported else ""
        if len(video_paths) == 2:
            filter_parts.append(
                f"[0:v][1:v]xfade=transition={transitions[0]}:duration={transition_duration}:offset={offsets[0]:.3f}{easing_param}[vout]"
            )
            if has_audio:
                filter_parts.append(
                    f"[0:a][1:a]acrossfade=d={transition_duration}[aout]"
                )
                map_args = ["-map", "[vout]", "-map", "[aout]"]
            else:
                map_args = ["-map", "[vout]"]
        else:
            v_prev = "[0:v]"
            a_prev = "[0:a]"
            for i in range(len(video_paths) - 1):
                v_out = "[vout]" if i == len(video_paths) - 2 else f"[v{i}]"
                a_out = "[aout]" if i == len(video_paths) - 2 else f"[a{i}]"
                filter_parts.append(
                    f"{v_prev}[{i+1}:v]xfade=transition={transitions[i]}:duration={transition_duration}:offset={offsets[i]:.3f}{easing_param}{v_out}"
                )
                if has_audio:
                    filter_parts.append(
                        f"{a_prev}[{i+1}:a]acrossfade=d={transition_duration}{a_out}"
                    )
                v_prev = v_out
                a_prev = a_out
            if has_audio:
                map_args = ["-map", "[vout]", "-map", "[aout]"]
            else:
                map_args = ["-map", "[vout]"]

        filter_complex = ";".join(filter_parts)


        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_complex
        ] + map_args + [
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-crf", "18", "-profile:v", "high", "-level", "4.1",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-preset", x264_preset,
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

    def _check_ffmpeg_easing_support(self) -> bool:
        """检测 FFmpeg xfade 是否支持 easing=（gyan 等常见构建通常不支持）。"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-h", "filter=xfade"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            text = (result.stdout or "") + (result.stderr or "")
            return "easing" in text.lower()
        except Exception:
            return False

    # ========== 工具方法 ==========

    def _run_cmd(self, cmd: list, step_name: str, cwd: str = None,
                 timeout: int = 120, shell: bool = False):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                shell=shell,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                stderr = result.stderr[-500:] if result.stderr else ""
                print(f"[RenderSkill] ⚠️ {step_name}警告: {stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{step_name}超时（{timeout}秒）")
        except Exception as e:
            raise RuntimeError(f"{step_name}失败: {e}")
