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


def init_agent():
    """初始化 Agent"""
    global _agent
    from python_agent.config import get_dashscope_api_key
    from python_agent.agent import VideoShortsAgent

    api_key = get_dashscope_api_key()
    _agent = VideoShortsAgent(
        api_key=api_key,
        llm_model="qwen3.5-flash",
        whisper_model="./faster-whisper-large-v3"
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

def process_agent(video_path, user_prompt):
    """Agent 模式：LLM 自主完成整个流程"""
    if not video_path:
        return "请先上传视频", "", None

    if isinstance(video_path, dict):
        video_path = video_path.get("video", video_path.get("name", ""))

    if not user_prompt or not user_prompt.strip():
        user_prompt = "帮我从这个视频中提取最精彩的片段做成短视频"

    # 捕获 Agent 日志
    capture = LogCapture()
    capture.start()

    try:
        result = _agent.run(
            user_message=user_prompt,
            video_path=video_path
        )
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
    task_dir = os.path.join("output", f"task_{task_id}")
    video_file = os.path.join(task_dir, "output_short.mp4")
    if os.path.exists(video_file):
        output_video = video_file

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
                gr.Markdown("> AI 自主思考并决策，自动完成 转录→分析→渲染 全流程")

                with gr.Row():
                    with gr.Column(scale=1):
                        agent_video = gr.Video(label="📤 上传视频")
                        agent_prompt = gr.Textbox(
                            label="💬 指令（可选）",
                            value="帮我从这个视频中提取最精彩的片段做成短视频",
                            lines=2
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
                    inputs=[agent_video, agent_prompt],
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
