"""
VideoShortsAgent Gradio Web 界面

两种模式：
- Agent 模式：LLM 自主决策，展示思考过程
- Pipeline 模式：手动分步执行

启动方式：
    python -m python_agent.app
"""
import os
import sys
import json
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

def process_agent(video_path, video_url, user_prompt, task_dir,
                  transcribe_mode="local", groq_api_key=""):
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
                            transcribe_mode = gr.Radio(
                                choices=["local", "groq"],
                                value="local",
                                label="转录模式",
                                info="local：本地 faster-whisper（较慢）；groq：Groq API（极快，需 API Key）"
                            )
                            groq_api_key = gr.Textbox(
                                label="Groq API Key",
                                placeholder="gsk_xxxx...",
                                type="password",
                                lines=1
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
                            transcribe_mode, groq_api_key],
                    outputs=[agent_reply, agent_logs, agent_output]
                )

            # Tab 2: 一键处理（简化版）
            with gr.Tab("⚡ 一键处理"):
                gr.Markdown("> 上传视频，一键自动完成全流程")

                with gr.Row():
                    with gr.Column(scale=1):
                        pipeline_video = gr.Video(label="📤 上传视频")
                        pipeline_btn = gr.Button("🚀 一键处理", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        pipeline_reply = gr.Markdown(label="📋 处理结果")
                        pipeline_steps = gr.Textbox(
                            label="📊 执行步骤", lines=5, interactive=False
                        )
                        pipeline_output = gr.Video(label="📹 输出短视频")

                with gr.Accordion("📜 执行日志", open=False):
                    pipeline_logs = gr.Textbox(
                        label="日志", lines=15, max_lines=30,
                        interactive=False, elem_classes="log-box"
                    )

                pipeline_btn.click(
                    fn=process_pipeline,
                    inputs=[pipeline_video],
                    outputs=[pipeline_reply, pipeline_steps, pipeline_logs, pipeline_output]
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
