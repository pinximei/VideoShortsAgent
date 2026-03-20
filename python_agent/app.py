"""
VideoShortsAgent Gradio Web 界面

Agent 模式：LLM 自主决策，自动完成 转录 → 分析 → 配音 → 渲染 全流程

启动方式：
    python -m python_agent.app
"""
import os
import sys
import json
import subprocess
import traceback
import threading
import queue
import io

# ========== Agent 引用 ==========
_agent = None


def init_agent(transcribe_mode="", groq_api_key=""):
    """初始化 Agent"""
    global _agent
    from python_agent.config import get_config
    from python_agent.agent import VideoShortsAgent

    cfg = get_config()
    _agent = VideoShortsAgent(
        api_key=cfg.llm_api_key,
        llm_model=cfg.llm_model,
        whisper_model=cfg.whisper_model_path,
        transcribe_mode=transcribe_mode or cfg.transcribe_mode,
        groq_api_key=groq_api_key or cfg.groq_api_key
    )


class LogCapture:
    """捕获 print 输出用于实时显示"""

    def __init__(self):
        self.logs = []
        self._old_stdout = None

    def start(self):
        self._old_stdout = sys.stdout
        sys.stdout = self

    def stop(self):
        if self._old_stdout:
            sys.stdout = self._old_stdout
            self._old_stdout = None

    def write(self, text):
        if text.strip():
            self.logs.append(text)
        if self._old_stdout:
            self._old_stdout.write(text)

    def flush(self):
        if self._old_stdout:
            self._old_stdout.flush()

    def get_text(self):
        return "".join(self.logs)


# ========== 处理函数 ==========


def _correct_transcript_with_llm(segments: list) -> list:
    """用 LLM 对转录文本进行翻译纠错（委托给 TranslateSkill）"""
    from python_agent.skills.translate_skill import TranslateSkill
    return TranslateSkill().execute(segments)


def process_subtitle(video_path, video_url, task_dir_input, transcribe_mode="local", groq_api_key=""):
    """固定流水线：转录 → LLM 纠错 → ASS 字幕 → FFmpeg 烧录"""
    has_task_dir = task_dir_input and task_dir_input.strip()
    if not video_path and (not video_url or not video_url.strip()) and not has_task_dir:
        return "请上传视频、输入 URL 或指定任务目录", "", None

    if isinstance(video_path, dict):
        video_path = video_path.get("video", video_path.get("name", ""))

    # Groq Key 降级
    if not groq_api_key or not groq_api_key.strip():
        from python_agent.config import get_groq_api_key
        groq_api_key = get_groq_api_key()

    capture = LogCapture()
    capture.start()

    try:
        import uuid
        import shutil

        # ① 确定任务目录和视频来源
        if has_task_dir:
            task_dir = task_dir_input.strip()
            if not os.path.isdir(task_dir):
                return f"❌ 任务目录不存在: {task_dir}", "", None
            # 找视频文件
            local_video = None
            for fname in os.listdir(task_dir):
                if fname.endswith((".mp4", ".mkv", ".webm", ".avi")) and "output" not in fname:
                    local_video = os.path.join(task_dir, fname)
                    break
            if not local_video:
                return "❌ 任务目录中找不到视频文件", "", None
        else:
            task_id = uuid.uuid4().hex[:8]
            task_dir = os.path.join("output", f"subtitle_{task_id}")
            os.makedirs(task_dir, exist_ok=True)

        # ② 获取视频（URL 下载、本地复制、或已有目录）
        if not has_task_dir:
            if video_url and video_url.strip() and not video_path:
                print(f"[字幕] 步骤 0: 下载视频...")
                from python_agent.skills.download_skill import DownloadSkill
                downloader = DownloadSkill()
                local_video = downloader.execute(video_url.strip(), task_dir)
                print(f"[字幕] 下载完成: {local_video}")
            else:
                video_ext = os.path.splitext(video_path)[1]
                local_video = os.path.join(task_dir, f"source_video{video_ext}")
                shutil.copy2(video_path, local_video)
        print(f"[字幕] 📁 任务: {task_dir}")

        # ③ 转录（已有 transcript.json 则跳过）
        transcript_path = os.path.join(task_dir, "transcript.json")
        if os.path.exists(transcript_path):
            print(f"[字幕] ✅ 转录文件已存在，跳过转录")
        else:
            print(f"\n[字幕] 步骤 1/4: 语音转文字 ({transcribe_mode})...")
            from python_agent.skills.transcribe_skill import TranscribeSkill
            transcriber = TranscribeSkill(
                model_path="./faster-whisper-large-v3",
                mode=transcribe_mode,
                groq_api_key=groq_api_key
            )
            transcript_path, lang = transcriber.execute(local_video, task_dir)

        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_data = json.load(f)
        segments = transcript_data.get("segments", [])
        lang = transcript_data.get("language", "unknown")
        print(f"[字幕] 转录完成: {len(segments)} 段, 语言={lang}")

        # ② 翻译纠错
        print(f"\n[字幕] 步骤 2/5: 翻译纠错...")
        corrected_segments = _correct_transcript_with_llm(segments)

        # ③ TTS 中文配音（并发批处理，大幅提速）
        print(f"\n[字幕] 步骤 3/5: 生成中文配音...")
        tts_dir = os.path.join(task_dir, "tts_segments")
        os.makedirs(tts_dir, exist_ok=True)
        import edge_tts
        import asyncio
        from python_agent.config import get_config
        _tts_voice = get_config().tts_voice

        def _get_audio_duration(path):
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", path],
                capture_output=True, text=True, timeout=10
            )
            try:
                return float(r.stdout.strip())
            except:
                return 0.0

        async def _generate_one(text, out_path):
            communicate = edge_tts.Communicate(text, _tts_voice, rate="+25%")
            await communicate.save(out_path)

        async def _generate_batch(tasks):
            """并发生成一批 TTS"""
            await asyncio.gather(*[_generate_one(t, p) for t, p in tasks])

        # 收集需要生成的任务
        tts_tasks = []
        for idx, seg in enumerate(corrected_segments):
            tts_path = os.path.join(tts_dir, f"seg_{idx:04d}.mp3")
            tts_tasks.append((seg["text"], tts_path, seg))

        # 并发批处理（每批 10 个）
        BATCH_SIZE = 10
        tts_ok_count = 0
        total = len(tts_tasks)
        for batch_start in range(0, total, BATCH_SIZE):
            batch = tts_tasks[batch_start:batch_start + BATCH_SIZE]
            batch_items = [(text, path) for text, path, _ in batch]
            try:
                asyncio.run(_generate_batch(batch_items))
            except Exception as e:
                print(f"  ⚠️ 批次 TTS 失败: {e}")

            # 对本批生成的文件做变速检查
            for text, path, seg in batch:
                if os.path.exists(path) and os.path.getsize(path) > 100:
                    seg_duration = seg["end"] - seg["start"]
                    tts_dur = _get_audio_duration(path)
                    if tts_dur > 0 and tts_dur > seg_duration and seg_duration > 0.5:
                        speed = min(tts_dur / seg_duration, 1.5)
                        tmp_path = path + ".tmp.mp3"
                        subprocess.run([
                            "ffmpeg", "-y", "-i", path,
                            "-af", f"atempo={speed:.2f}",
                            "-c:a", "libmp3lame", tmp_path
                        ], capture_output=True, timeout=15)
                        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 100:
                            os.replace(tmp_path, path)
                    tts_ok_count += 1

            done = min(batch_start + BATCH_SIZE, total)
            print(f"  已生成 {done}/{total} 段")
        print(f"[字幕] TTS 完成: {tts_ok_count}/{total} 段")

        # ④ 合成音轨（concat 拼接：静音填充 + TTS 顺序拼接，音量零损失）
        print(f"\n[字幕] 步骤 4/5: 合成音轨 + 生成字幕...")
        from python_agent.skills.render_skill import RenderSkill
        renderer = RenderSkill()
        video_duration = renderer._get_duration(local_video)
        full_audio_path = os.path.join(task_dir, "full_tts_audio.wav")
        import shutil

        # 为每段 TTS 生成 [静音填充 + TTS] 的 wav 片段，并记录实际时间
        concat_dir = os.path.join(task_dir, "concat_parts")
        os.makedirs(concat_dir, exist_ok=True)
        concat_list_path = os.path.join(task_dir, "concat_list.txt")
        current_pos = 0.0  # 当前音轨播放位置
        part_count = 0
        actual_timeline = []  # 记录每段 TTS 在音轨中的实际位置

        with open(concat_list_path, "w", encoding="utf-8") as concat_f:
            for idx, seg in enumerate(corrected_segments):
                tts_path = os.path.join(tts_dir, f"seg_{idx:04d}.mp3")
                if not os.path.exists(tts_path) or os.path.getsize(tts_path) < 100:
                    continue

                seg_start = seg["start"]
                gap = seg_start - current_pos

                # 如果有间隔，先填充静音
                if gap > 0.05:
                    silence_part = os.path.join(concat_dir, f"silence_{part_count:04d}.wav")
                    subprocess.run([
                        "ffmpeg", "-y", "-f", "lavfi", "-i",
                        "anullsrc=r=24000:cl=mono",
                        "-t", f"{gap:.3f}", silence_part
                    ], capture_output=True, timeout=10)
                    if os.path.exists(silence_part):
                        concat_f.write(f"file '{silence_part}'\n")
                        current_pos += gap
                        part_count += 1

                # 转换 TTS 为统一格式 wav
                tts_wav = os.path.join(concat_dir, f"tts_{part_count:04d}.wav")
                subprocess.run([
                    "ffmpeg", "-y", "-i", tts_path,
                    "-ar", "24000", "-ac", "1", "-acodec", "pcm_s16le",
                    tts_wav
                ], capture_output=True, timeout=10)

                if os.path.exists(tts_wav):
                    concat_f.write(f"file '{tts_wav}'\n")
                    tts_dur = _get_audio_duration(tts_wav)
                    # 记录实际时间：此段 TTS 从 current_pos 开始
                    actual_timeline.append({
                        "text": seg["text"],
                        "start": current_pos,
                        "end": current_pos + tts_dur
                    })
                    current_pos += tts_dur
                    part_count += 1

            # 尾部静音填充到视频结尾
            tail_gap = video_duration - current_pos
            if tail_gap > 0.1:
                tail_silence = os.path.join(concat_dir, f"silence_{part_count:04d}.wav")
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=24000:cl=mono",
                    "-t", f"{tail_gap:.3f}", tail_silence
                ], capture_output=True, timeout=10)
                if os.path.exists(tail_silence):
                    concat_f.write(f"file '{tail_silence}'\n")

        # concat 拼接（零音量损失）
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1",
            full_audio_path
        ], capture_output=True, text=True, timeout=120)
        print(f"[字幕] 音轨拼接完成 ({part_count} 个片段)")

        # 生成 ASS 字幕（用音频实际时间轴 + 长文本换行）
        # 根据视频宽度动态计算每行字数（字体 72px，左右 margin 各 40px）
        probe_r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "v:0",
             "-show_entries", "stream=width", "-of", "csv=p=0", local_video],
            capture_output=True, text=True, timeout=10
        )
        try:
            video_width = int(probe_r.stdout.strip())
        except:
            video_width = 1920
        font_size = 72
        # 中文字体实际宽度约为字号的 0.8 倍（含 Spacing=2）
        max_chars_per_line = int((video_width - 80) / (font_size * 0.8))
        print(f"[字幕] 视频宽度={video_width}px, 每行最多{max_chars_per_line}字")

        def _wrap_text(text, max_chars=max_chars_per_line):
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
                    # 找不到标点，向后找最近的标点断行
                    for p in ['，', '。', '、', '；', ',', ' ']:
                        pos = text.find(p, max_chars)
                        if pos > 0:
                            cut = pos + 1
                            break
                if cut <= 0:
                    if len(text) > max_chars * 1.5:
                        cut = len(text) // 2  # 太长就从中间断
                    else:
                        break  # 不太长就不断行
                lines.append(text[:cut])
                text = text[cut:]
            if text:
                lines.append(text)
            return "\\N".join(lines)

        sentences = []
        for s in actual_timeline:
            wrapped = _wrap_text(s["text"])
            # 去掉每行尾部标点（只保留中间的标点）
            final_lines = []
            for line in wrapped.split("\\N"):
                final_lines.append(line.rstrip("，。、；！？,.;!?"))
            wrapped = "\\N".join(final_lines)
            sentences.append({"text": wrapped, "start": s["start"], "end": s["end"]})
        ass_path = os.path.join(task_dir, "subtitle.ass")
        renderer._generate_ass("", video_duration, ass_path, sentences=sentences)

        # ⑤ 烧录字幕 + 替换音频（一步完成）
        print(f"\n[字幕] 步骤 5/5: 烧录字幕 + 替换音频...")
        output_path = os.path.join(task_dir, "output_with_subtitle.mp4")
        ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

        if os.path.exists(full_audio_path) and os.path.getsize(full_audio_path) > 0:
            # 有配音：去原声 + 加配音 + 加字幕
            final_cmd = [
                "ffmpeg", "-y",
                "-i", local_video,
                "-i", full_audio_path,
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
            renderer._burn_subtitle(local_video, ass_path, output_path)
            final_cmd = None

        if final_cmd:
            renderer._run_cmd(final_cmd, "烧录字幕+配音", timeout=600)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"\n[字幕] ✅ 完成! {output_path} ({size_mb:.1f} MB)")
            status = f"✅ **翻译配音完成**\n\n- 字幕条数: {len(corrected_segments)}\n- TTS 配音: {tts_ok_count} 段\n- 输出: `{output_path}`\n- 大小: {size_mb:.1f} MB"
            return status, capture.get_text(), output_path
        else:
            return "❌ 烧录失败，输出文件不存在", capture.get_text(), None

    except Exception as e:
        traceback.print_exc()
        return f"❌ 处理失败: {e}", capture.get_text(), None
    finally:
        capture.stop()

def process_agent(video_path, video_url, user_prompt, task_dir,
                  transcribe_mode="local", groq_api_key="", render_mode="remotion"):
    """按需重新初始化 Agent（如果转录模式变更）"""
    global _agent

    # Groq Key：UI 输入优先，否则从 .env 读取
    if not groq_api_key or not groq_api_key.strip():
        from python_agent.config import get_groq_api_key
        groq_api_key = get_groq_api_key()

    need_reinit = (
        _agent is None
        or _agent.transcribe_skill.mode != transcribe_mode
    )
    if need_reinit:
        init_agent(transcribe_mode=transcribe_mode, groq_api_key=groq_api_key)

    existing_task_dir = None
    effective_video = None

    # 优先级：任务目录 > URL > 上传视频
    if task_dir and task_dir.strip():
        task_dir = task_dir.strip()
        if not os.path.isdir(task_dir):
            return f"❌ 任务目录不存在: {task_dir}", "", None
        existing_task_dir = task_dir

        # 清理上次生成的输出文件，避免重复叠加
        for old_output in ["output_short.mp4"]:
            old_path = os.path.join(task_dir, old_output)
            if os.path.exists(old_path):
                os.remove(old_path)
        # 清理 TTS 临时目录
        tts_seg_dir = os.path.join(task_dir, "tts_segments")
        if os.path.isdir(tts_seg_dir):
            import shutil
            shutil.rmtree(tts_seg_dir, ignore_errors=True)

        # 扫描原始视频文件（排除生成的输出文件）
        generated_names = {"output_short.mp4"}
        for fname in os.listdir(task_dir):
            if fname.endswith((".mp4", ".mkv", ".webm", ".avi")) and fname not in generated_names:
                effective_video = os.path.join(task_dir, fname)
                break
        # 检查 transcript.json 是否存在
        transcript_path = os.path.join(task_dir, "transcript.json")
        has_transcript = os.path.exists(transcript_path)
        # 自动构造指令：明确告诉 Agent 用原始视频
        if not user_prompt or not user_prompt.strip():
            parts = []
            if has_transcript:
                parts.append(f"转录文件已存在: {transcript_path}，跳过 transcribe 步骤。")
            if effective_video:
                parts.append(f"原始视频文件: {effective_video}（注意：必须使用这个原始视频，不要使用目录中其他已生成的视频）")
            parts.append("请直接从 analyze 开始，提取精彩片段，配音并渲染短视频。")
            user_prompt = "\n".join(parts)
    elif video_url and video_url.strip():
        if not user_prompt or not user_prompt.strip():
            user_prompt = f"请先下载这个视频 {video_url} ，然后提取多个精彩片段，加上亮点字幕，拼接成短视频"
        elif video_url not in user_prompt:
            user_prompt = f"视频链接: {video_url}\n{user_prompt}"
    elif video_path:
        if isinstance(video_path, dict):
            video_path = video_path.get("video", video_path.get("name", ""))
        effective_video = video_path
    else:
        return "请上传视频、输入视频 URL，或指定已有任务目录", "", None

    if not user_prompt or not user_prompt.strip():
        user_prompt = "提取视频中多个精彩片段，加上亮点字幕，拼接成一个短视频"

    # 捕获 Agent 日志
    capture = LogCapture()
    capture.start()

    try:
        run_kwargs = {
            "user_message": user_prompt,
            "video_path": effective_video if (not video_url or not video_url.strip()) else None,
        }
        if existing_task_dir:
            run_kwargs["task_dir"] = existing_task_dir
        run_kwargs["use_remotion"] = (render_mode == "remotion")
        result = _agent.run(**run_kwargs)
    except Exception as e:
        traceback.print_exc()
        capture.stop()
        return f"❌ Agent 执行失败: {e}", capture.get_text(), None
    finally:
        capture.stop()

    # 提取结果
    agent_reply = result.get("reply", "")
    log_text = capture.get_text()
    task_id = result.get("task_id", "")

    # 查找输出视频
    output_video = None
    if existing_task_dir:
        search_dir = existing_task_dir
    else:
        search_dir = os.path.join("output", f"task_{task_id}")
    for candidate in ["output_short.mp4", "dubbed_video.mp4"]:
        video_file = os.path.join(search_dir, candidate)
        if os.path.exists(video_file):
            output_video = video_file
            break

    return agent_reply, log_text, output_video


def process_pipeline(video_path):
    """Pipeline 模式：分步执行"""
    if not video_path:
        return "请先上传视频", "", "", None

    if isinstance(video_path, dict):
        video_path = video_path.get("video", video_path.get("name", ""))

    capture = LogCapture()
    capture.start()

    try:
        result = _agent.run(
            user_message="帮我从这个视频中提取最精彩的片段做成短视频",
            video_path=video_path
        )
    except Exception as e:
        traceback.print_exc()
        capture.stop()
        return f"❌ 处理失败: {e}", "", capture.get_text(), None
    finally:
        capture.stop()

    agent_reply = result.get("reply", "")
    log_text = capture.get_text()
    task_id = result.get("task_id", "")

    output_video = None
    task_dir = os.path.join("output", f"task_{task_id}")
    video_file = os.path.join(task_dir, "output_short.mp4")
    if os.path.exists(video_file):
        output_video = video_file

    # 提取步骤信息
    steps = result.get("steps", [])
    steps_text = "\n".join(
        f"Step {s['iteration']}: {s['tool']}({json.dumps(s['args'], ensure_ascii=False)[:100]})"
        for s in steps
    )

    return agent_reply, steps_text, log_text, output_video


# ========== 构建界面 ==========

def create_app():
    import gradio as gr

    with gr.Blocks(
        title="VideoShortsAgent",
    ) as app:

        gr.Markdown("# 🎬 VideoShortsAgent", elem_classes="main-title")
        gr.Markdown("上传长视频 → AI Agent 自动提取金句 → 生成短视频切片", elem_classes="subtitle")

        with gr.Tabs():
            # Tab 1: Agent 模式（核心）
            with gr.Tab("🤖 Agent 模式"):
                gr.Markdown("> 支持上传视频、YouTube 链接，或指定已有任务目录（跳过转录）")

                with gr.Row():
                    with gr.Column(scale=1):
                        agent_video = gr.Video(label="📤 上传视频（方式一）")
                        agent_url = gr.Textbox(
                            label="🔗 或输入视频 URL（方式二）",
                            placeholder="粘贴 YouTube / Bilibili 链接...",
                            lines=1
                        )
                        agent_task_dir = gr.Textbox(
                            label="📂 或指定已有任务目录（方式三，跳过转录）",
                            placeholder="如 output/task_abc12345（含视频和 transcript.json）",
                            lines=1
                        )
                        agent_prompt = gr.Textbox(
                            label="💬 指令（可选）",
                            value="提取视频中多个精彩片段，加上亮点字幕和特效，拼接成一个短视频",
                            lines=2
                        )
                        with gr.Accordion("⚙️ 转录设置", open=False):
                            from python_agent.config import get_groq_api_key
                            _env_groq_key = get_groq_api_key()
                            _default_mode = "groq" if _env_groq_key else "local"
                            transcribe_mode = gr.Radio(
                                choices=["groq", "local"],
                                value=_default_mode,
                                label="转录模式",
                                info="groq：Groq API（极快，推荐）；local：本地 faster-whisper（较慢）"
                            )
                            groq_api_key = gr.Textbox(
                                label="Groq API Key",
                                placeholder="gsk_xxxx...",
                                type="password",
                                lines=1
                            )
                        with gr.Accordion("🎨 渲染设置", open=False):
                            render_mode = gr.Radio(
                                choices=["remotion", "ffmpeg"],
                                value="remotion",
                                label="字幕渲染模式",
                                info="remotion：高级动态特效（默认）；ffmpeg：经典 ASS 字幕（快速稳定）"
                            )
                        agent_btn = gr.Button("🚀 开始处理", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        agent_reply = gr.Markdown(label="📋 Agent 回复")
                        agent_output = gr.Video(label="📹 输出短视频")

                with gr.Accordion("📜 Agent 执行日志", open=False):
                    agent_logs = gr.Textbox(
                        label="实时日志", lines=20, max_lines=40,
                        interactive=False, elem_classes="log-box"
                    )

                agent_btn.click(
                    fn=process_agent,
                    inputs=[agent_video, agent_url, agent_prompt, agent_task_dir,
                            transcribe_mode, groq_api_key, render_mode],
                    outputs=[agent_reply, agent_logs, agent_output]
                )


            # Tab 2: 翻译字幕（固定流水线）
            with gr.Tab("📝 中文字幕"):
                gr.Markdown("> 给视频添加中文字幕（固定流程：转录 → LLM 纠错 → 字幕烧录）")

                with gr.Row():
                    with gr.Column(scale=1):
                        sub_video = gr.Video(label="📤 上传视频（方式一）")
                        sub_url = gr.Textbox(
                            label="🔗 或输入视频 URL（方式二）",
                            placeholder="粘贴 YouTube / Bilibili 链接...",
                            lines=1
                        )
                        sub_task_dir = gr.Textbox(
                            label="📂 或指定已有任务目录（方式三，跳过转录）",
                            placeholder="如 output/task_abc12345",
                            lines=1
                        )
                        with gr.Accordion("⚙️ 设置", open=False):
                            from python_agent.config import get_groq_api_key as _get_key
                            _key = _get_key()
                            sub_transcribe_mode = gr.Radio(
                                choices=["groq", "local"],
                                value="groq" if _key else "local",
                                label="转录模式"
                            )
                            sub_groq_key = gr.Textbox(
                                label="Groq API Key", placeholder="gsk_xxxx...",
                                type="password", lines=1
                            )
                        sub_btn = gr.Button("📝 生成字幕", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        sub_status = gr.Markdown(label="📋 处理状态")
                        sub_output = gr.Video(label="📹 带字幕视频")

                with gr.Accordion("📜 执行日志", open=False):
                    sub_logs = gr.Textbox(
                        label="日志", lines=15, max_lines=30,
                        interactive=False, elem_classes="log-box"
                    )

                sub_btn.click(
                    fn=process_subtitle,
                    inputs=[sub_video, sub_url, sub_task_dir, sub_transcribe_mode, sub_groq_key],
                    outputs=[sub_status, sub_logs, sub_output]
                )


            # Tab 3: 文本生视频
            with gr.Tab("✨ 文本生视频"):
                gr.Markdown("> 输入文本或 URL → 选择场景和风格 → 一键生成短视频（支持上传图片或 AI 自动配图）")

                # 加载模板配置（从 templates/ 目录）
                from python_agent.template_loader import load_all as _load_templates
                _templates = _load_templates()

                _scene_names = {v["name"]: k for k, v in _templates["scene_templates"].items()}
                _style_names = {v["name"]: k for k, v in _templates["visual_styles"].items()}
                _bgm_names = {v["name"]: k for k, v in _templates["bgm_library"].items()}

                def _fetch_url_content(url):
                    """从 URL 提取网页正文"""
                    if not url or not url.strip():
                        return "", "❌ 请输入 URL"
                    url = url.strip()
                    try:
                        import urllib.request
                        import re as _re
                        req = urllib.request.Request(url, headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        })
                        with urllib.request.urlopen(req, timeout=15) as resp:
                            html = resp.read().decode("utf-8", errors="ignore")
                        # 提取 title
                        title_m = _re.search(r'<title[^>]*>(.*?)</title>', html, _re.DOTALL | _re.IGNORECASE)
                        title = title_m.group(1).strip() if title_m else ""
                        # 移除 script/style
                        html = _re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', '', html, flags=_re.DOTALL | _re.IGNORECASE)
                        # 移除 HTML 标签
                        text = _re.sub(r'<[^>]+>', '\n', html)
                        # 清理空白
                        text = _re.sub(r'\n\s*\n', '\n', text)
                        text = _re.sub(r'[ \t]+', ' ', text)
                        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
                        # 取前 200 行，避免太长
                        content = '\n'.join(lines[:200])
                        if title:
                            content = f"{title}\n\n{content}"
                        if len(content) < 20:
                            return "", f"⚠️ 网页内容太少，请直接粘贴文本"
                        return content, f"✅ 已提取 {len(content)} 字符"
                    except Exception as e:
                        return "", f"❌ 提取失败: {e}"

                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Group():
                            t2v_url = gr.Textbox(
                                label="🔗 输入 URL（可选）",
                                placeholder="粘贴招聘页面或公司官网链接...",
                                lines=1
                            )
                            t2v_fetch_btn = gr.Button("📥 提取网页内容", size="sm")
                        t2v_text = gr.Textbox(
                            label="📝 输入文本",
                            placeholder="粘贴招聘 JD、公司简介、功能描述...（或从 URL 提取）",
                            lines=8
                        )
                        t2v_scene = gr.Radio(
                            choices=list(_scene_names.keys()),
                            value=list(_scene_names.keys())[0],
                            label="📋 场景类型"
                        )
                        t2v_style = gr.Radio(
                            choices=list(_style_names.keys()),
                            value=list(_style_names.keys())[0],
                            label="🎨 视觉风格"
                        )

                        with gr.Accordion("📷 图片设置", open=False):
                            t2v_images = gr.File(
                                label="上传图片（可选，LLM 按文件名匹配）",
                                file_count="multiple", type="filepath"
                            )
                            t2v_ai_img = gr.Checkbox(
                                label="🎨 AI 自动配图（Pexels 搜图 + AI 生图）",
                                value=True
                            )

                        with gr.Accordion("🎵 BGM 和语音", open=False):
                            t2v_bgm = gr.Dropdown(
                                choices=list(_bgm_names.keys()),
                                value=list(_bgm_names.keys())[0],
                                label="📀 预置背景音乐"
                            )
                            gr.Markdown("--- 或 在线搜索 ---")
                            with gr.Row():
                                t2v_bgm_query = gr.Textbox(
                                    label="🔍 搜索在线 BGM",
                                    placeholder="输入英文关键词，如 upbeat technology...",
                                    lines=1, scale=3
                                )
                                t2v_bgm_search_btn = gr.Button("🔍 搜索", size="sm", scale=1)
                            t2v_bgm_results = gr.Radio(
                                choices=[], label="🎵 搜索结果",
                                visible=False
                            )
                            # 隐藏字段：存储选中的在线 BGM 信息
                            t2v_bgm_selected_info = gr.State(value=None)
                            t2v_voice = gr.Dropdown(
                                choices=[
                                    "zh-CN-YunxiNeural", "zh-CN-YunjianNeural",
                                    "zh-CN-YunyangNeural", "zh-CN-XiaoxiaoNeural",
                                    "zh-CN-XiaoyiNeural",
                                ],
                                value="zh-CN-YunxiNeural",
                                label="🗣️ 语音角色"
                            )

                        t2v_compose_btn = gr.Button("📝 生成脚本", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        # 脚本预览区
                        t2v_script_display = gr.JSON(label="📋 脚本预览（可编辑）", visible=False)
                        t2v_render_btn = gr.Button("🚀 确认，开始渲染", variant="primary", size="lg", visible=False)

                        # 输出区
                        t2v_output_video = gr.Video(label="📹 生成的视频")
                        t2v_xhs_text = gr.Textbox(
                            label="📱 小红书发布文案（一键复制）",
                            lines=8, interactive=True, visible=False
                        )
                        t2v_doc_text = gr.Textbox(
                            label="📄 功能文档（Markdown）",
                            lines=6, interactive=True, visible=False
                        )
                        t2v_status = gr.Markdown("")

                with gr.Accordion("📜 执行日志", open=False):
                    t2v_logs = gr.Textbox(
                        label="日志", lines=15, max_lines=30,
                        interactive=False, elem_classes="log-box"
                    )

                # ── 处理函数 ──

                def _step1_compose(text, scene_name, style_name, images, ai_img):
                    """第一步：生成脚本预览"""
                    if not text or not text.strip():
                        return (gr.update(), gr.update(), gr.update(),
                                "❌ 请输入文本内容", "")

                    capture = LogCapture()
                    capture.start()
                    try:
                        from python_agent.skills.compose_skill import ComposeSkill
                        scene_key = _scene_names.get(scene_name, "general")
                        # 提取图片文件名
                        img_names = []
                        if images:
                            img_names = [os.path.basename(p) for p in images]

                        skill = ComposeSkill()
                        script = skill.execute(text, scene_key, img_names, ai_img)

                        return (
                            gr.update(value=script, visible=True),    # script_display
                            gr.update(visible=True),                   # render_btn
                            gr.update(),                               # status
                            f"✅ 脚本生成完成，共 {len(script.get('slides', []))} 个段落。请检查内容后点击「🚀 确认，开始渲染」",
                            capture.get_text()
                        )
                    except Exception as e:
                        traceback.print_exc()
                        return (gr.update(), gr.update(), gr.update(),
                                f"❌ 脚本生成失败: {e}", capture.get_text())
                    finally:
                        capture.stop()

                def _step2_render(script_json, text, scene_name, style_name,
                                  images, ai_img, bgm_name, voice,
                                  bgm_selected_info):
                    """第二步：确认后渲染视频"""
                    if not script_json:
                        return (None, gr.update(), gr.update(), "❌ 请先生成脚本", "")

                    capture = LogCapture()
                    capture.start()
                    try:
                        import uuid
                        from python_agent.skills.image_resolver_skill import ImageResolverSkill
                        from python_agent.skills.dubbing_skill import DubbingSkill
                        from python_agent.skills.render_slides_skill import RenderSlidesSkill
                        from python_agent.skills.publish_skill import PublishSkill

                        scene_key = _scene_names.get(scene_name, "general")
                        style_key = _style_names.get(style_name, "tech_blue")
                        bgm_key = _bgm_names.get(bgm_name, "none")
                        visual_style = _templates["visual_styles"].get(style_key, {})
                        bgm_config = _templates["bgm_library"].get(bgm_key, {})

                        task_id = uuid.uuid4().hex[:8]
                        task_dir = os.path.join("output", f"text2video_{task_id}")
                        os.makedirs(task_dir, exist_ok=True)

                        slides = script_json.get("slides", [])
                        if not slides:
                            return (None, gr.update(), gr.update(),
                                    "❌ 脚本中没有 slides", capture.get_text())

                        # 1. 解析图片
                        print("[Text2Video] 步骤 1/4: 解析图片...")
                        images_dir = None
                        if images:
                            images_dir = os.path.join(task_dir, "user_images")
                            os.makedirs(images_dir, exist_ok=True)
                            import shutil
                            for p in images:
                                shutil.copy2(p, os.path.join(images_dir, os.path.basename(p)))

                        resolver = ImageResolverSkill()
                        slides = resolver.execute(slides, images_dir, ai_img, task_dir)

                        # 2. TTS 配音
                        print("[Text2Video] 步骤 2/4: 生成 TTS 配音...")
                        dubbing_skill = DubbingSkill(voice=voice)
                        # 构建 DubbingSkill 需要的格式
                        clips_with_tts = []
                        for s in slides:
                            clips_with_tts.append({
                                "tts_text": s.get("tts_text", ""),
                            })
                        tts_result = dubbing_skill.execute(clips_with_tts, task_dir)
                        # tts_result 是包含每段 TTS 信息的列表
                        tts_clips = tts_result if isinstance(tts_result, list) else []

                        # 3. 渲染视频
                        print("[Text2Video] 步骤 3/4: 渲染视频...")
                        bgm_path = None

                        # 优先使用在线搜索的 BGM
                        if bgm_selected_info and isinstance(bgm_selected_info, dict):
                            from python_agent.skills.music_search_skill import MusicSearchSkill
                            music_skill = MusicSearchSkill()
                            online_bgm = music_skill.download(
                                bgm_selected_info["id"],
                                bgm_selected_info["preview_url"],
                                task_dir
                            )
                            if online_bgm:
                                bgm_path = online_bgm
                                print(f"[Text2Video] 使用在线 BGM: {bgm_selected_info.get('name', '')}")

                        # 回退到预置 BGM
                        if not bgm_path and bgm_config.get("path"):
                            bgm_full = os.path.join(
                                os.path.dirname(os.path.dirname(__file__)),
                                bgm_config["path"]
                            )
                            if os.path.exists(bgm_full):
                                bgm_path = bgm_full

                        renderer = RenderSlidesSkill()
                        video_path = renderer.execute(
                            slides, tts_clips, visual_style, task_dir, bgm_path
                        )

                        # 4. 生成发布文案
                        print("[Text2Video] 步骤 4/4: 生成发布文案...")
                        publish_skill = PublishSkill()
                        publish_result = publish_skill.execute(script_json, text, scene_key)

                        xhs_formatted = publish_skill.format_xiaohongshu(publish_result)
                        doc_text = publish_result.get("doc", "")

                        return (
                            video_path,
                            gr.update(value=xhs_formatted, visible=True),
                            gr.update(value=doc_text, visible=True),
                            f"✅ 视频生成完成！\n\n📁 任务目录: `{task_dir}`",
                            capture.get_text()
                        )
                    except Exception as e:
                        traceback.print_exc()
                        return (None, gr.update(), gr.update(),
                                f"❌ 渲染失败: {e}", capture.get_text())
                    finally:
                        capture.stop()

                def _search_bgm(query):
                    """在线搜索 BGM"""
                    if not query or not query.strip():
                        return gr.update(), gr.update(), None, "❌ 请输入搜索关键词"
                    from python_agent.skills.music_search_skill import MusicSearchSkill
                    skill = MusicSearchSkill()
                    if not skill.is_available():
                        return gr.update(), gr.update(), None, "⚠️ 未配置 FREESOUND_API_KEY，请在 .env 中配置"
                    results = skill.search(query.strip())
                    if not results:
                        return gr.update(choices=[], visible=False), gr.update(), None, "未找到相关音乐，请换个关键词"
                    # 构建选项列表
                    choices = []
                    results_map = {}
                    for r in results:
                        label = f"{r['name']} ({r['duration']:.0f}s) by {r['username']}"
                        choices.append(label)
                        results_map[label] = r
                    # 用闭包存储映射
                    _search_bgm._results_map = results_map
                    return (
                        gr.update(choices=choices, visible=True, value=choices[0]),
                        gr.update(),
                        results_map.get(choices[0]),
                        f"✅ 找到 {len(choices)} 首相关音乐"
                    )
                _search_bgm._results_map = {}

                def _on_bgm_select(selection):
                    """用户选择 BGM 时更新 state"""
                    return _search_bgm._results_map.get(selection)

                t2v_bgm_search_btn.click(
                    fn=_search_bgm,
                    inputs=[t2v_bgm_query],
                    outputs=[t2v_bgm_results, t2v_bgm, t2v_bgm_selected_info, t2v_status]
                )

                t2v_bgm_results.change(
                    fn=_on_bgm_select,
                    inputs=[t2v_bgm_results],
                    outputs=[t2v_bgm_selected_info]
                )

                t2v_fetch_btn.click(
                    fn=_fetch_url_content,
                    inputs=[t2v_url],
                    outputs=[t2v_text, t2v_status]
                )

                t2v_compose_btn.click(
                    fn=_step1_compose,
                    inputs=[t2v_text, t2v_scene, t2v_style, t2v_images, t2v_ai_img],
                    outputs=[t2v_script_display, t2v_render_btn, t2v_output_video,
                             t2v_status, t2v_logs]
                )

                t2v_render_btn.click(
                    fn=_step2_render,
                    inputs=[t2v_script_display, t2v_text, t2v_scene, t2v_style,
                            t2v_images, t2v_ai_img, t2v_bgm, t2v_voice,
                            t2v_bgm_selected_info],
                    outputs=[t2v_output_video, t2v_xhs_text, t2v_doc_text,
                             t2v_status, t2v_logs]
                )


            # Tab 4: 设置
            with gr.Tab("⚙️ 设置"):
                gr.Markdown("> 修改配置后点击「保存」，将写入 `.env` 文件（部分设置需重启后生效）")

                from python_agent.config import get_config as _gc
                _cfg = _gc()

                with gr.Accordion("🤖 LLM 模型配置", open=True):
                    set_api_key = gr.Textbox(
                        label="API Key", value=_cfg.llm_api_key[:8] + "..." if len(_cfg.llm_api_key) > 8 else _cfg.llm_api_key,
                        type="password", lines=1,
                        info="LLM 服务的 API Key"
                    )
                    set_base_url = gr.Textbox(
                        label="API 地址 (Base URL)", value=_cfg.llm_base_url, lines=1,
                        info="支持任何 OpenAI 兼容 API（DashScope / DeepSeek / Ollama 等）"
                    )
                    with gr.Row():
                        set_model = gr.Textbox(
                            label="主模型", value=_cfg.llm_model, lines=1,
                            info="Agent 和分析使用的模型"
                        )
                        set_translate_model = gr.Textbox(
                            label="翻译模型", value=_cfg.llm_translate_model, lines=1,
                            info="字幕翻译使用的模型"
                        )

                with gr.Accordion("🎙️ 语音配置", open=True):
                    set_tts_voice = gr.Dropdown(
                        label="默认语音角色",
                        choices=[
                            "zh-CN-YunyangNeural",
                            "zh-CN-YunjianNeural",
                            "zh-CN-YunxiNeural",
                            "zh-CN-XiaoxiaoNeural",
                            "zh-CN-XiaoyiNeural",
                        ],
                        value=_cfg.tts_voice,
                        info="TTS 配音的默认语音角色"
                    )
                    set_groq_key = gr.Textbox(
                        label="Groq API Key", type="password", lines=1,
                        value=_cfg.groq_api_key[:8] + "..." if len(_cfg.groq_api_key) > 8 else _cfg.groq_api_key,
                        info="用于 Groq Whisper 转录（推荐）"
                    )

                with gr.Accordion("🎬 视频参数", open=True):
                    with gr.Row():
                        set_max_iter = gr.Number(
                            label="Agent 最大迭代次数", value=_cfg.max_iterations,
                            precision=0, minimum=1, maximum=50,
                            info="Agent 单次任务最多执行多少轮"
                        )
                        set_max_dur = gr.Number(
                            label="最大视频时长 (秒)", value=_cfg.max_video_duration,
                            precision=0, minimum=10, maximum=300,
                            info="输出视频的最大时长上限"
                        )
                    set_port = gr.Number(
                        label="服务端口", value=_cfg.server_port,
                        precision=0, minimum=1024, maximum=65535,
                        info="Web UI 端口（修改后需重启）"
                    )

                save_status = gr.Markdown("")
                save_btn = gr.Button("💾 保存配置到 .env", variant="primary", size="lg")

                def _save_settings(api_key, base_url, model, translate_model,
                                   tts_voice, groq_key, max_iter, max_dur, port):
                    from python_agent.config import save_to_env
                    updates = {}
                    # 只保存用户实际修改的值（跳过密码框的占位符）
                    if api_key and not api_key.endswith("..."):
                        updates["DASHSCOPE_API_KEY"] = api_key
                    if base_url:
                        updates["LLM_BASE_URL"] = base_url
                    if model:
                        updates["LLM_MODEL"] = model
                    if translate_model:
                        updates["LLM_TRANSLATE_MODEL"] = translate_model
                    if tts_voice:
                        updates["TTS_VOICE"] = tts_voice
                    if groq_key and not groq_key.endswith("..."):
                        updates["GROQ_API_KEY"] = groq_key
                    if max_iter:
                        updates["MAX_ITERATIONS"] = str(int(max_iter))
                    if max_dur:
                        updates["MAX_VIDEO_DURATION"] = str(int(max_dur))
                    if port:
                        updates["SERVER_PORT"] = str(int(port))

                    if not updates:
                        return "⚠️ 没有需要保存的变更"
                    return save_to_env(updates)

                save_btn.click(
                    fn=_save_settings,
                    inputs=[set_api_key, set_base_url, set_model, set_translate_model,
                            set_tts_voice, set_groq_key, set_max_iter, set_max_dur, set_port],
                    outputs=[save_status]
                )


        gr.Markdown("---")
        gr.Markdown(
            "**VideoShortsAgent** | "
            "Powered by Qwen + Whisper + FFmpeg + Remotion | "
            "[GitHub](https://github.com/pinximei/VideoShortsAgent)",
            elem_classes="subtitle"
        )

    return app


if __name__ == "__main__":
    init_agent()
    from python_agent.config import get_config
    import gradio as gr
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=get_config().server_port,
        share=False,
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="blue",
        ),
        css="""
        .main-title { text-align: center; margin-bottom: 0; }
        .subtitle { text-align: center; color: #666; margin-top: 0; }
        .log-box textarea { font-family: 'Consolas', 'Monaco', monospace !important; font-size: 12px !important; }
        """
    )
