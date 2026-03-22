"""
RenderSlidesSkill - 幻灯片式视频渲染技能

将 ComposeSkill 生成的结构化脚本渲染为视频：
1. 逐 slide 调用 Remotion 渲染画面
2. 为每个 slide 附加 TTS 音频
3. xfade 转场拼接所有 slides
4. 混入 BGM（可选）
"""
import os
import json
import shutil
import subprocess

# Remotion 项目目录（相对于项目根）
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REMOTION_DIR = os.path.join(_PROJECT_ROOT, "remotion_effects")


class RenderSlidesSkill:
    """幻灯片式视频渲染"""

    def __init__(self, width=1080, height=1920):
        self.fps = 30
        self.width = width
        self.height = height
        self._check_remotion()

    def _check_remotion(self):
        """检查 Remotion 是否可用"""
        self._remotion_available = os.path.exists(
            os.path.join(REMOTION_DIR, "node_modules")
        )
        if not self._remotion_available:
            print("[RenderSlidesSkill] ⚠️ Remotion 未安装，将使用 FFmpeg 纯渲染")

    def execute(self, slides: list, tts_clips: list,
                visual_style: dict, output_dir: str,
                bgm_path: str = None) -> str:
        """渲染视频"""
        os.makedirs(output_dir, exist_ok=True)
        segment_paths = []

        print(f"[RenderSlidesSkill] 开始渲染 {len(slides)} 个 slides...")

        for i, slide in enumerate(slides):
            tts_clip = tts_clips[i] if i < len(tts_clips) else None
            if not tts_clip:
                print(f"  [Slide {i+1}] ⚠️ 无 TTS 信息，跳过")
                continue

            duration = tts_clip.get("duration", 5.0)
            tts_audio_path = tts_clip.get("path")
            sentences = tts_clip.get("sentences", [])

            print(f"  [Slide {i+1}/{len(slides)}] {slide.get('type', '?')}: "
                  f"{slide.get('heading', '')[:30]}... ({duration:.1f}s)")

            # 1. 渲染画面（纯视频，无音频）
            video_path = os.path.join(output_dir, f"slide_{i}_video.mp4")
            self._render_slide_video(slide, visual_style, duration, sentences,
                                     video_path, output_dir, i)

            if not os.path.exists(video_path):
                print(f"  [Slide {i+1}] ⚠️ 画面渲染失败，跳过")
                continue

            # 1.5 冻结末帧延长 0.3 秒（片段间呼吸暂停）
            self._freeze_extend(video_path, 0.3)

            # 2. 附加 TTS 音频
            segment_path = os.path.join(output_dir, f"segment_{i}.mp4")
            audio_ok = False

            if tts_audio_path and os.path.exists(tts_audio_path):
                audio_ok = self._attach_audio_with_pad(video_path, tts_audio_path, segment_path, 0.3)
                if not audio_ok:
                    print(f"  [Slide {i+1}] ⚠️ 音频附加失败，添加静音音轨")

            if not audio_ok:
                self._add_silent_audio(video_path, duration + 0.3, segment_path)

            if os.path.exists(segment_path) and os.path.getsize(segment_path) > 1024:
                segment_paths.append(segment_path)
            else:
                print(f"  [Slide {i+1}] ⚠️ segment 生成失败")

        if not segment_paths:
            raise RuntimeError("没有成功渲染的 slides")

        # 3. 转场拼接
        print(f"[RenderSlidesSkill] 拼接 {len(segment_paths)} 个片段...")
        concat_path = os.path.join(output_dir, "concat_output.mp4")
        self._concat_slides(segment_paths, slides, concat_path, output_dir)

        if not os.path.exists(concat_path) or os.path.getsize(concat_path) < 1024:
            print("[RenderSlidesSkill] ⚠️ xfade 拼接失败，使用简单拼接")
            self._simple_concat(segment_paths, concat_path, output_dir)

        # 4. 混入 BGM
        final_path = os.path.join(output_dir, "output_slides.mp4")
        if bgm_path and os.path.exists(bgm_path):
            print("[RenderSlidesSkill] 混入 BGM...")
            self._mix_bgm(concat_path, bgm_path, final_path)
        else:
            shutil.copy2(concat_path, final_path)

        # 清理中间文件
        self._cleanup(output_dir, segment_paths, concat_path)

        file_size = os.path.getsize(final_path) / (1024 * 1024)
        print(f"[RenderSlidesSkill] ✅ 输出: {final_path} ({file_size:.1f}MB)")
        return final_path

    # ========== 渲染单个 slide ==========

    def _render_slide_video(self, slide, style, duration, sentences,
                            output_path, output_dir, index):
        """渲染单个 slide 的画面视频（无音频）"""
        total_frames = max(1, int(duration * self.fps))
        if self._remotion_available:
            self._render_with_remotion(slide, style, total_frames, sentences,
                                       output_path, output_dir, index)
        else:
            self._render_with_ffmpeg(slide, style, duration, output_path)

    def _render_with_remotion(self, slide, style, frames, sentences,
                               output_path, output_dir, index):
        """Remotion 渲染"""
        composition_map = {
            "title_card": "TitleCard",
            "content_card": "ContentCard",
            "cta_card": "CTACard",
        }
        composition = composition_map.get(slide.get("type", "content_card"), "ContentCard")

        # 时轨对齐逻辑 (Audio-Visual Sync)
        heading_trigger = slide.get("heading_trigger", "")
        heading_start_frame = 0
        if heading_trigger and sentences:
            for seq in sentences:
                if heading_trigger in seq.get("text", ""):
                    heading_start_frame = int(seq.get("start", 0) * self.fps)
                    break
        
        raw_bullets = slide.get("bullets", [])
        final_bullets = []
        bullet_start_frames = []
        
        for b_idx, b in enumerate(raw_bullets):
            if isinstance(b, dict):
                text = b.get("text", "")
                trigger = b.get("trigger", "")
            else:
                text = str(b)
                trigger = ""
            
            final_bullets.append(text)
            
            # 如果没匹配到，默认在 heading 后递增弹出
            m_frame = heading_start_frame + 15 + b_idx * 15
            if trigger and sentences:
                for seq in sentences:
                    if trigger in seq.get("text", ""):
                        m_frame = int(seq.get("start", 0) * self.fps)
                        break
            bullet_start_frames.append(m_frame)
            
        visual_props = slide.get("visual_design", {})

        props = {
            "heading": slide.get("heading", ""),
            "subheading": slide.get("subheading", ""),
            "bullets": final_bullets,
            "ctaText": slide.get("cta_text", ""),
            "hookText": slide.get("hook_text", ""),
            "captionStyle": slide.get("caption_style", style.get("caption_style", "spring")),
            "colors": style.get("colors", ["#0f0c29", "#302b63"]),
            "textColor": style.get("text_color", "#ffffff"),
            "accentColor": style.get("accent_color", "#00d2ff"),
            "cameraPan": visual_props.get("camera_pan", "zoom-in"),
            "particleType": visual_props.get("particle_type", "glow"),
            "decorationStyle": visual_props.get("decoration_style", "none"),
            "textEffect": visual_props.get("text_effect", "classic"),
            "layoutStyle": visual_props.get("layout_style", "center"),
            "colorMood": visual_props.get("color_mood", ""),
            "headingStartFrame": heading_start_frame,
            "bulletStartFrames": bullet_start_frames,
        }
        if sentences:
            props["sentences"] = sentences
        if slide.get("image_path"):
            # 将图片复制到 Remotion public/images/ 目录，使用相对路径加载
            # （Chromium 安全策略阻止 file:/// 协议，public 目录由 Remotion 自动 serve）
            pub_images_dir = os.path.join(REMOTION_DIR, "public", "images")
            os.makedirs(pub_images_dir, exist_ok=True)
            src_img = os.path.abspath(slide["image_path"])
            ext = os.path.splitext(src_img)[1] or ".png"
            pub_img_name = f"slide_{index}{ext}"
            pub_img_path = os.path.join(pub_images_dir, pub_img_name)
            shutil.copy2(src_img, pub_img_path)
            props["imagePath"] = f"/images/{pub_img_name}"

        props_path = os.path.abspath(os.path.join(output_dir, f"slide_props_{index}.json"))
        with open(props_path, "w", encoding="utf-8") as f:
            json.dump(props, f, ensure_ascii=False)

        seq_dir = os.path.join(output_dir, f"slide_seq_{index}")
        os.makedirs(seq_dir, exist_ok=True)

        cmd = [
            "npx", "remotion", "render", "src/index.tsx", composition,
            f"--output={os.path.abspath(seq_dir).replace(chr(92), '/')}",
            f"--props={props_path.replace(chr(92), '/')}",
            "--image-format=png", "--sequence",
            f"--width={self.width}", f"--height={self.height}",
            f"--frames=0-{frames - 1}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=600, cwd=REMOTION_DIR, shell=True)
            if result.returncode != 0:
                print(f"  ⚠️ Remotion 渲染失败，降级为 FFmpeg")
                self._render_with_ffmpeg(slide, style, frames / self.fps, output_path)
                return
        except subprocess.TimeoutExpired:
            print(f"  ⚠️ Remotion 渲染超时，降级为 FFmpeg")
            self._render_with_ffmpeg(slide, style, frames / self.fps, output_path)
            return

        import glob, re
        png_files = sorted(glob.glob(os.path.join(seq_dir, "*.png")))
        if png_files:
            first = os.path.basename(png_files[0])
            m = re.match(r"(.+?)(\d+)(\.png)$", first)
            if m:
                pattern = os.path.join(seq_dir, f"{m.group(1)}%0{len(m.group(2))}d.png")
            else:
                pattern = os.path.join(seq_dir, "%d.png")
            pattern = pattern.replace("\\", "/")
            subprocess.run([
                "ffmpeg", "-y", "-framerate", str(self.fps), "-i", pattern,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "18", "-profile:v", "high", "-level", "4.1",
                "-preset", "medium",
                output_path
            ], capture_output=True, text=True, timeout=300)

        if os.path.exists(seq_dir):
            shutil.rmtree(seq_dir, ignore_errors=True)
        if os.path.exists(props_path):
            os.remove(props_path)
        # 清理复制到 public/images/ 的图片
        if slide.get("image_path"):
            pub_img = os.path.join(REMOTION_DIR, "public", "images", f"slide_{index}{os.path.splitext(slide['image_path'])[1] or '.png'}")
            if os.path.exists(pub_img):
                os.remove(pub_img)
        if not os.path.exists(output_path):
            self._render_with_ffmpeg(slide, style, frames / self.fps, output_path)

    def _render_with_ffmpeg(self, slide, style, duration, output_path):
        """FFmpeg 纯渲染降级（渐变背景 + 居中文字）"""
        colors = style.get("colors", ["#0f0c29", "#302b63"])
        text_color = style.get("text_color", "#ffffff").lstrip("#")
        title = slide.get("heading", "")
        # FFmpeg drawtext 需要转义特殊字符
        safe_title = title.replace("'", "\\'").replace(":", "\\:")

        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={colors[0].lstrip('#')}:s={self.width}x{self.height}:d={duration}:r={self.fps}",
            "-vf", f"drawtext=text='{safe_title}':fontsize=72:fontcolor={text_color}:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", "-profile:v", "high", "-level", "4.1",
            "-preset", "medium",
            "-t", str(duration), output_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print(f"  ⚠️ FFmpeg drawtext 失败: {r.stderr[-200:]}")
            # 超级降级：纯色块
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"color=c={colors[0].lstrip('#')}:s={self.width}x{self.height}:d={duration}:r={self.fps}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "18", "-profile:v", "high", "-level", "4.1",
                "-preset", "medium",
                "-t", str(duration), output_path
            ], capture_output=True, text=True, timeout=60)

    # ========== 音频处理 ==========

    def _attach_audio(self, video_path, audio_path, output_path):
        """将 TTS 音频附加到视频，返回是否成功"""
        dur = self._get_duration(audio_path)
        if dur <= 0:
            print(f"  ⚠️ TTS 音频无效: {audio_path}")
            return False

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path, "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", output_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print(f"  ⚠️ attach_audio 失败: {r.stderr[-200:]}")
            return False
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
            return False

        # 验证输出有音频流
        check = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", output_path],
            capture_output=True, text=True, timeout=5
        )
        if "audio" not in check.stdout:
            print(f"  ⚠️ 输出视频无音频流")
            return False
        return True

    def _add_silent_audio(self, video_path, duration, output_path):
        """为视频添加静音音轨"""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac",
            "-t", str(duration), output_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            print(f"  ⚠️ add_silent_audio 失败: {r.stderr[-150:]}")
            shutil.copy2(video_path, output_path)

    def _freeze_extend(self, video_path, pad_seconds=0.3):
        """用 tpad 滤镜冻结末帧延长视频（原地替换）"""
        padded_path = video_path + ".padded.mp4"
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"tpad=stop_mode=clone:stop_duration={pad_seconds:.3f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", "-profile:v", "high", "-level", "4.1",
            "-preset", "medium", "-an",
            padded_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0 and os.path.exists(padded_path):
            os.replace(padded_path, video_path)
        else:
            print(f"  ⚠️ tpad 冻结延长失败，保持原视频")
            if os.path.exists(padded_path):
                os.remove(padded_path)

    def _attach_audio_with_pad(self, video_path, audio_path, output_path, pad_seconds=0.3):
        """将 TTS 音频附加到视频，并用 apad 延长音频以匹配冻结帧"""
        dur = self._get_duration(audio_path)
        if dur <= 0:
            print(f"  ⚠️ TTS 音频无效: {audio_path}")
            return False

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path, "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-af", f"apad=pad_dur={pad_seconds:.3f}",
            "-shortest", output_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print(f"  ⚠️ attach_audio_with_pad 失败: {r.stderr[-200:]}")
            return False
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
            return False

        # 验证输出有音频流
        check = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", output_path],
            capture_output=True, text=True, timeout=5
        )
        if "audio" not in check.stdout:
            print(f"  ⚠️ 输出视频无音频流")
            return False
        return True

    # ========== 拼接 ==========

    def _concat_slides(self, segment_paths, slides, output_path, output_dir):
        """xfade 转场拼接"""
        if len(segment_paths) == 1:
            shutil.copy2(segment_paths[0], output_path)
            return

        transition_duration = 0.8
        durations = [self._get_duration(p) for p in segment_paths]
        if any(d <= 0 for d in durations):
            print("[RenderSlidesSkill] ⚠️ 部分片段时长无效，使用简单拼接")
            self._simple_concat(segment_paths, output_path, output_dir)
            return

        valid_t = {"fade", "wipeleft", "wiperight", "wipeup", "wipedown",
                   "slideup", "slidedown", "slideleft", "slideright",
                   "circleopen", "circleclose", "dissolve", "pixelize",
                   "diagtl", "diagtr", "diagbl", "diagbr",
                   "smoothleft", "smoothright", "smoothup", "smoothdown",
                   "horzopen", "horzclose", "vertopen", "vertclose",
                   "radial", "circlecrop", "rectcrop", "distance", 
                   "hrslice", "vrslice", "vlslice", "hblur", "hlslice"}
        transitions = []
        for i in range(len(segment_paths) - 1):
            t = slides[i].get("transition_to_next", "fade") or "fade" if i < len(slides) else "fade"
            transitions.append(t if t in valid_t else "fade")

        # 检测 FFmpeg 是否支持 easing 参数（FFmpeg 7.0+）
        easing_supported = self._check_ffmpeg_easing_support()
        easing_param = ":easing=easeInOutCubic" if easing_supported else ""

        inputs = []
        for path in segment_paths:
            inputs += ["-i", path]

        filter_parts = []
        if len(segment_paths) == 2:
            offset = max(0, durations[0] - transition_duration)
            filter_parts.append(
                f"[0:v][1:v]xfade=transition={transitions[0]}:duration={transition_duration}:offset={offset}{easing_param}[vout]")
            filter_parts.append(f"[0:a][1:a]acrossfade=d={transition_duration}[aout]")
            map_args = ["-map", "[vout]", "-map", "[aout]"]
        else:
            cum = 0
            for i in range(len(segment_paths) - 1):
                inv = f"[{i}:v]" if i == 0 else f"[v{i}]"
                outv = "[vout]" if i == len(segment_paths) - 2 else f"[v{i+1}]"
                off = cum + durations[i] - transition_duration
                filter_parts.append(
                    f"{inv}[{i+1}:v]xfade=transition={transitions[i]}:duration={transition_duration}:offset={max(0,off)}{easing_param}{outv}")
                cum += durations[i] - transition_duration
            for i in range(len(segment_paths) - 1):
                ina = f"[{i}:a]" if i == 0 else f"[a{i}]"
                outa = "[aout]" if i == len(segment_paths) - 2 else f"[a{i+1}]"
                filter_parts.append(f"{ina}[{i+1}:a]acrossfade=d={transition_duration}{outa}")
            map_args = ["-map", "[vout]", "-map", "[aout]"]

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", ";".join(filter_parts)
        ] + map_args + [
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-crf", "18", "-profile:v", "high", "-level", "4.1",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-preset", "medium", output_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f"[RenderSlidesSkill] ⚠️ xfade 拼接失败: {r.stderr[-300:]}")

    def _simple_concat(self, segment_paths, output_path, output_dir):
        """简单拼接（无转场，保证音频）"""
        concat_list = os.path.join(output_dir, "concat_list.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for p in segment_paths:
                f.write(f"file '{os.path.abspath(p).replace(chr(92), '/')}'\n")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-crf", "18", "-profile:v", "high", "-level", "4.1",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-preset", "medium", output_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f"[RenderSlidesSkill] ⚠️ simple_concat 失败: {r.stderr[-200:]}")
        if os.path.exists(concat_list):
            os.remove(concat_list)

    # ========== BGM ==========

    def _mix_bgm(self, video_path, bgm_path, output_path, bgm_volume=0.12):
        """将 BGM 混入视频"""
        video_duration = self._get_duration(video_path)
        check = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
            capture_output=True, text=True, timeout=5
        )
        has_audio = "audio" in check.stdout

        fade_out_start = max(0, video_duration - 2)
        if has_audio:
            fc = (f"[1:a]volume={bgm_volume},lowpass=f=8000,afade=t=in:st=0:d=1.5,"
                  f"afade=t=out:st={fade_out_start}:d=2[bgm];"
                  f"[0:a][bgm]amix=inputs=2:duration=first:weights=1 {bgm_volume}[aout]")
            map_args = ["-map", "0:v", "-map", "[aout]"]
        else:
            fc = (f"[1:a]volume={bgm_volume},lowpass=f=8000,afade=t=in:st=0:d=1.5,"
                  f"afade=t=out:st={fade_out_start}:d=2[bgm]")
            map_args = ["-map", "0:v", "-map", "[bgm]"]

        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-stream_loop", "-1", "-i", bgm_path,
            "-filter_complex", fc
        ] + map_args + [
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", output_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print(f"[RenderSlidesSkill] ⚠️ BGM 混音失败: {r.stderr[-200:]}")
            shutil.copy2(video_path, output_path)

    # ========== 工具 ==========

    def _get_duration(self, path):
        """获取媒体文件时长"""
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", path],
                capture_output=True, text=True, timeout=10)
            return float(r.stdout.strip())
        except Exception:
            return 5.0

    def _check_ffmpeg_easing_support(self) -> bool:
        """检测 FFmpeg 是否支持 xfade easing 参数（实际探测）"""
        try:
            # 用短命令实际测试 easing 参数是否被识别
            result = subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=2x2:d=0.1:r=1",
                 "-f", "lavfi", "-i", "color=c=white:s=2x2:d=0.1:r=1",
                 "-filter_complex", "[0:v][1:v]xfade=duration=0.05:offset=0.05:easing=linear[v]",
                 "-map", "[v]", "-frames:v", "1", "-f", "null", "-"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            pass
        return False

    def _cleanup(self, output_dir, segment_paths, concat_path):
        """清理中间文件"""
        for p in segment_paths:
            if os.path.exists(p):
                os.remove(p)
        import glob
        for p in glob.glob(os.path.join(output_dir, "slide_*_video.mp4")):
            os.remove(p)
        if os.path.exists(concat_path):
            os.remove(concat_path)
