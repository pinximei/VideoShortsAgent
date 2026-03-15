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


def init_agent(transcribe_mode="local", groq_api_key=""):
    """初始化 Agent"""
    global _agent
    from python_agent.config import get_dashscope_api_key
    from python_agent.agent import VideoShortsAgent

    api_key = get_dashscope_api_key()
    _agent = VideoShortsAgent(
        api_key=api_key,
        llm_model="qwen3.5-flash",
        whisper_model="./faster-whisper-large-v3",
        transcribe_mode=transcribe_mode,
        groq_api_key=groq_api_key
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
    """用 LLM 对转录文本进行纠错（分批处理，保持时间戳不变）"""
    from python_agent.config import get_dashscope_api_key
    from openai import OpenAI

    BATCH_SIZE = 50
    api_key = get_dashscope_api_key()
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        timeout=120,
    )

    all_corrected = []
    total_batches = (len(segments) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"[字幕] LLM 纠错: {len(segments)} 条片段，分 {total_batches} 批处理")

    for batch_idx in range(total_batches):
        batch = segments[batch_idx * BATCH_SIZE: (batch_idx + 1) * BATCH_SIZE]
        full_text = "\n".join(
            f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in batch
        )

        prompt = f"""你是视频配音字幕专家。将每条语音识别文本翻译为中文。

**要求**：
- 逐条翻译 保持原始条数不变
- 保持每条的 start 和 end 时间戳不变
- 准确传达原文含义 不要丢失重要内容
- 语言简洁自然 去掉口语废话（所以、那么、嗯）
- 保留必要的标点符号（逗号、句号）
- 技术术语必须正确（Agent Scale→Agent Skills）

**规则**：
1. 输入多少条 输出必须同样多条
2. 每条时间戳原样保留
3. 直接返回纯 JSON 数组

原始文本：
{full_text}

返回：[{{"start": 0.0, "end": 3.5, "text": "准确中文翻译"}}]"""

        try:
            print(f"  批次 {batch_idx + 1}/{total_batches} ({len(batch)} 条)...", end=" ")
            response = client.chat.completions.create(
                model="qwen-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            corrected = json.loads(result_text)
            all_corrected.extend(corrected)
            print(f"✅ {len(corrected)} 条")
        except Exception as e:
            print(f"⚠️ 失败({e})，使用原文")
            all_corrected.extend(batch)

    print(f"[字幕] LLM 纠错完成，共 {len(all_corrected)} 条字幕")
    return all_corrected


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

        # ③ TTS 中文配音（自然语速，不变速）
        print(f"\n[字幕] 步骤 3/5: 生成中文配音...")
        tts_dir = os.path.join(task_dir, "tts_segments")
        os.makedirs(tts_dir, exist_ok=True)
        import edge_tts
        import asyncio

        async def _generate_tts(text, out_path):
            communicate = edge_tts.Communicate(text, "zh-CN-YunxiNeural", rate="+25%")
            await communicate.save(out_path)

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

        tts_ok_count = 0
        for idx, seg in enumerate(corrected_segments):
            tts_path = os.path.join(tts_dir, f"seg_{idx:04d}.mp3")
            seg_duration = seg["end"] - seg["start"]
            try:
                asyncio.run(_generate_tts(seg["text"], tts_path))
                # 如果 TTS 超出时间窗口，加速适配
                tts_dur = _get_audio_duration(tts_path)
                if tts_dur > 0 and tts_dur > seg_duration and seg_duration > 0.5:
                    speed = min(tts_dur / seg_duration, 1.5)
                    tmp_path = tts_path + ".tmp.mp3"
                    subprocess.run([
                        "ffmpeg", "-y", "-i", tts_path,
                        "-af", f"atempo={speed:.2f}",
                        "-c:a", "libmp3lame", tmp_path
                    ], capture_output=True, timeout=15)
                    if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 100:
                        os.replace(tmp_path, tts_path)
                tts_ok_count += 1
            except Exception as e:
                pass  # 失败的段不生成，后续跳过
            if (idx + 1) % 50 == 0:
                print(f"  已生成 {idx + 1}/{len(corrected_segments)} 段")
        print(f"[字幕] TTS 完成: {tts_ok_count}/{len(corrected_segments)} 段")

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
    import gradio as gr
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
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
