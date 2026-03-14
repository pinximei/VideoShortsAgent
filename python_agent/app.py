"""
VideoShortsAgent Gradio Web 界面

提供可视化的操作界面：上传视频 → 查看转录 → 分析金句 → 生成短视频

启动方式：
    python -m python_agent.app
"""
import os
import json
import gradio as gr

from python_agent.config import get_dashscope_api_key
from python_agent.skills.transcribe_skill import TranscribeSkill
from python_agent.skills.analysis_skill import AnalysisSkill
from python_agent.skills.render_skill import RenderSkill

# ========== 全局状态 ==========
# 延迟初始化，首次使用时才加载模型（避免启动太慢）
_skills = {}


def _get_skills():
    """延迟加载 Skills（首次调用时初始化）"""
    if not _skills:
        api_key = get_dashscope_api_key()
        _skills["transcribe"] = TranscribeSkill(
            model_path="./faster-whisper-large-v3"
        )
        _skills["analysis"] = AnalysisSkill(api_key=api_key, model="qwen3")
        _skills["render"] = RenderSkill()
    return _skills


# ========== 处理函数 ==========

def process_transcribe(video_path):
    """Step 1: 转录视频"""
    if not video_path:
        return "请先上传视频", None

    skills = _get_skills()
    output_dir = os.path.join("output", "gradio_task")
    os.makedirs(output_dir, exist_ok=True)

    try:
        result_path = skills["transcribe"].execute(video_path, output_dir)

        with open(result_path, "r", encoding="utf-8") as f:
            transcript = json.load(f)

        # 格式化为可读文本
        text_lines = []
        for seg in transcript:
            text_lines.append(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")

        display_text = "\n".join(text_lines)
        return display_text, result_path

    except Exception as e:
        return f"❌ 转录失败: {e}", None


def process_analyze(transcript_path):
    """Step 2: 分析金句"""
    if not transcript_path:
        return "请先完成转录"

    skills = _get_skills()

    try:
        result = skills["analysis"].execute(transcript_path)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"❌ 分析失败: {e}"


def process_full_pipeline(video_path, progress=gr.Progress()):
    """一键处理：转录 → 分析 → 渲染"""
    if not video_path:
        return "请先上传视频", "", "", None

    skills = _get_skills()
    output_dir = os.path.join("output", "gradio_task")
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: 转录
    progress(0.1, desc="正在转录视频...")
    try:
        transcript_path = skills["transcribe"].execute(video_path, output_dir)
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = json.load(f)

        transcript_text = "\n".join(
            f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}" for s in transcript
        )
    except Exception as e:
        return f"❌ 转录失败: {e}", "", "", None

    # Step 2: 分析
    progress(0.5, desc="正在分析金句...")
    try:
        analysis = skills["analysis"].execute(transcript_path)
        analysis_text = json.dumps(analysis, ensure_ascii=False, indent=2)
    except Exception as e:
        return transcript_text, f"❌ 分析失败: {e}", "", None

    # Step 3: 渲染
    progress(0.8, desc="正在生成短视频...")
    try:
        output_video = skills["render"].execute(video_path, analysis, output_dir)
        render_text = f"✅ 输出: {output_video}"
    except Exception as e:
        render_text = f"❌ 渲染失败: {e}"
        output_video = None

    progress(1.0, desc="完成！")

    # 如果渲染是桩实现，输出文件不存在则不返回视频
    if output_video and not os.path.exists(output_video):
        output_video = None

    return transcript_text, analysis_text, render_text, output_video


# ========== 构建界面 ==========

def create_app():
    with gr.Blocks(title="VideoShortsAgent") as app:

        gr.Markdown("# 🎬 VideoShortsAgent")
        gr.Markdown("上传长视频 → AI 自动提取金句 → 生成短视频切片")

        with gr.Row():
            # 左侧：输入
            with gr.Column(scale=1):
                video_input = gr.Video(label="📤 上传视频")
                btn_full = gr.Button("🚀 一键处理", variant="primary", size="lg")

                gr.Markdown("---")
                gr.Markdown("#### 分步操作")
                btn_transcribe = gr.Button("📝 Step 1: 转录")
                btn_analyze = gr.Button("🔍 Step 2: 分析金句")

            # 右侧：输出
            with gr.Column(scale=2):
                transcript_output = gr.Textbox(
                    label="📝 转录结果",
                    lines=10,
                    max_lines=20,
                    interactive=False
                )
                analysis_output = gr.Textbox(
                    label="🔍 金句分析",
                    lines=4,
                    interactive=False
                )
                render_output = gr.Textbox(
                    label="🎨 渲染状态",
                    lines=2,
                    interactive=False
                )
                video_output = gr.Video(label="📹 输出短视频")

        # 隐藏状态：存储 transcript.json 的路径
        transcript_path_state = gr.State(None)

        # 绑定事件
        btn_transcribe.click(
            fn=process_transcribe,
            inputs=[video_input],
            outputs=[transcript_output, transcript_path_state]
        )

        btn_analyze.click(
            fn=process_analyze,
            inputs=[transcript_path_state],
            outputs=[analysis_output]
        )

        btn_full.click(
            fn=process_full_pipeline,
            inputs=[video_input],
            outputs=[transcript_output, analysis_output, render_output, video_output]
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False
    )
