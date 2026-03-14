"""
VideoShortsAgent Gradio Web 界面

提供可视化的操作界面：上传视频 → 查看转录 → 分析金句 → 生成短视频

启动方式：
    python -m python_agent.app
"""
import os
import sys
import json
import traceback

# ========== 全局 Skill 引用（启动后再加载） ==========
_transcribe_skill = None
_analysis_skill = None
_render_skill = None


def init_skills():
    """在 Gradio 启动后加载 Skills"""
    global _transcribe_skill, _analysis_skill, _render_skill

    from python_agent.config import get_dashscope_api_key
    from python_agent.skills.transcribe_skill import TranscribeSkill
    from python_agent.skills.analysis_skill import AnalysisSkill
    from python_agent.skills.render_skill import RenderSkill

    print("=" * 50)
    print("  正在初始化 Skills...")
    print("=" * 50)

    api_key = get_dashscope_api_key()
    _transcribe_skill = TranscribeSkill(model_path="./faster-whisper-large-v3")
    _analysis_skill = AnalysisSkill(api_key=api_key, model="qwen3-flash")
    _render_skill = RenderSkill()

    print("  所有 Skills 初始化完成 ✅")
    print("=" * 50)


# ========== 处理函数 ==========

def process_transcribe(video_path):
    """Step 1: 转录视频"""
    if not video_path:
        return "请先上传视频", None

    if isinstance(video_path, dict):
        video_path = video_path.get("video", video_path.get("name", ""))

    print(f"[转录] 视频路径: {video_path}")

    output_dir = os.path.join("output", "gradio_task")
    os.makedirs(output_dir, exist_ok=True)

    try:
        result_path = _transcribe_skill.execute(video_path, output_dir)

        with open(result_path, "r", encoding="utf-8") as f:
            transcript = json.load(f)

        text_lines = []
        for seg in transcript:
            text_lines.append(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")

        display_text = "\n".join(text_lines)
        return display_text, result_path

    except Exception as e:
        traceback.print_exc()
        return f"❌ 转录失败: {e}", None


def process_analyze(transcript_path):
    """Step 2: 分析金句"""
    if not transcript_path:
        return "请先完成转录"

    try:
        result = _analysis_skill.execute(transcript_path)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        traceback.print_exc()
        return f"❌ 分析失败: {e}"


def process_full_pipeline(video_path):
    """一键处理：转录 → 分析 → 渲染"""
    if not video_path:
        return "请先上传视频", "", "", None

    if isinstance(video_path, dict):
        video_path = video_path.get("video", video_path.get("name", ""))

    print(f"[一键处理] 视频路径: {video_path}")

    output_dir = os.path.join("output", "gradio_task")
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: 转录
    print("[一键处理] Step 1/3: 转录...")
    try:
        transcript_path = _transcribe_skill.execute(video_path, output_dir)
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = json.load(f)

        transcript_text = "\n".join(
            f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}" for s in transcript
        )
    except Exception as e:
        traceback.print_exc()
        return f"❌ 转录失败: {e}", "", "", None

    # Step 2: 分析
    print("[一键处理] Step 2/3: 分析金句...")
    try:
        analysis = _analysis_skill.execute(transcript_path)
        analysis_text = json.dumps(analysis, ensure_ascii=False, indent=2)
    except Exception as e:
        traceback.print_exc()
        return transcript_text, f"❌ 分析失败: {e}", "", None

    # Step 3: 渲染
    print("[一键处理] Step 3/3: 渲染...")
    try:
        output_video = _render_skill.execute(video_path, analysis, output_dir)
        render_text = f"✅ 输出: {output_video}"
    except Exception as e:
        traceback.print_exc()
        render_text = f"❌ 渲染失败: {e}"
        output_video = None

    if output_video and not os.path.exists(output_video):
        output_video = None

    print("[一键处理] 完成！")
    return transcript_text, analysis_text, render_text, output_video


def process_from_text(transcript_text, video_path):
    """从手动输入的转录文字开始处理（跳过转录步骤）"""
    if not transcript_text or not transcript_text.strip():
        return "请先输入转录文字", "", None

    print(f"[文字处理] 收到 {len(transcript_text)} 字符的转录文字")

    output_dir = os.path.join("output", "gradio_task")
    os.makedirs(output_dir, exist_ok=True)

    # 将文字保存为 transcript.json 供 AnalysisSkill 使用
    # 支持两种格式：
    #   1. 纯文字 → 包装成单条记录
    #   2. [时间] 文字 → 解析为带时间戳的结构
    import re
    segments = []
    for line in transcript_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # 尝试匹配 [1.0s - 3.0s] 文字 格式
        match = re.match(r'\[(\d+\.?\d*)s?\s*-\s*(\d+\.?\d*)s?\]\s*(.*)', line)
        if match:
            segments.append({
                "start": float(match.group(1)),
                "end": float(match.group(2)),
                "text": match.group(3)
            })
        else:
            # 纯文字，给个默认时间
            segments.append({
                "start": len(segments) * 5.0,
                "end": (len(segments) + 1) * 5.0,
                "text": line
            })

    transcript_path = os.path.join(output_dir, "transcript.json")
    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    print(f"[文字处理] 已保存 {len(segments)} 个片段到 {transcript_path}")

    # 分析金句
    print("[文字处理] 正在分析金句...")
    try:
        analysis = _analysis_skill.execute(transcript_path)
        analysis_text = json.dumps(analysis, ensure_ascii=False, indent=2)
    except Exception as e:
        traceback.print_exc()
        return f"❌ 分析失败: {e}", "", None

    # 渲染（如果有视频）
    render_text = ""
    output_video = None
    if video_path:
        if isinstance(video_path, dict):
            video_path = video_path.get("video", video_path.get("name", ""))
        print("[文字处理] 正在渲染...")
        try:
            output_video = _render_skill.execute(video_path, analysis, output_dir)
            render_text = f"✅ 输出: {output_video}"
        except Exception as e:
            render_text = f"❌ 渲染失败: {e}"
            output_video = None

        if output_video and not os.path.exists(output_video):
            output_video = None
    else:
        render_text = "⚠️ 未上传视频，跳过渲染"

    print("[文字处理] 完成！")
    return analysis_text, render_text, output_video


# ========== 构建界面 ==========

def create_app():
    import gradio as gr

    with gr.Blocks(title="VideoShortsAgent") as app:

        gr.Markdown("# 🎬 VideoShortsAgent")
        gr.Markdown("上传长视频 → AI 自动提取金句 → 生成短视频切片")

        with gr.Tabs():
            # Tab 1: 视频处理（完整流程）
            with gr.Tab("📹 视频处理"):
                with gr.Row():
                    with gr.Column(scale=1):
                        video_input = gr.Video(label="📤 上传视频")
                        btn_full = gr.Button("🚀 一键处理", variant="primary", size="lg")

                        gr.Markdown("---")
                        gr.Markdown("#### 分步操作")
                        btn_transcribe = gr.Button("📝 Step 1: 转录")
                        btn_analyze = gr.Button("🔍 Step 2: 分析金句")

                    with gr.Column(scale=2):
                        transcript_output = gr.Textbox(
                            label="📝 转录结果", lines=10, max_lines=20, interactive=False
                        )
                        analysis_output = gr.Textbox(
                            label="🔍 金句分析", lines=4, interactive=False
                        )
                        render_output = gr.Textbox(
                            label="🎨 渲染状态", lines=2, interactive=False
                        )
                        video_output = gr.Video(label="📹 输出短视频")

                transcript_path_state = gr.State(None)

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

            # Tab 2: 文字处理（粘贴转录文字，跳过转录步骤）
            with gr.Tab("📝 文字处理"):
                gr.Markdown("已有转录文字？直接粘贴，跳过转录步骤")
                with gr.Row():
                    with gr.Column(scale=1):
                        text_input = gr.Textbox(
                            label="📝 粘贴转录文字",
                            lines=12,
                            placeholder="支持两种格式：\n1. 纯文字（每行一句）\n2. [1.0s - 3.0s] 带时间戳文字",
                            interactive=True
                        )
                        text_video_input = gr.Video(label="📤 上传视频（可选，用于渲染）")
                        btn_from_text = gr.Button("🚀 分析并处理", variant="primary", size="lg")

                    with gr.Column(scale=1):
                        text_analysis_output = gr.Textbox(
                            label="🔍 金句分析", lines=6, interactive=False
                        )
                        text_render_output = gr.Textbox(
                            label="🎨 渲染状态", lines=2, interactive=False
                        )
                        text_video_output = gr.Video(label="📹 输出短视频")

                btn_from_text.click(
                    fn=process_from_text,
                    inputs=[text_input, text_video_input],
                    outputs=[text_analysis_output, text_render_output, text_video_output]
                )

    return app


if __name__ == "__main__":
    # 1. 先加载 Whisper 模型（不受 Gradio 超时限制）
    init_skills()

    # 2. 再启动 Gradio（此时模型已在内存中）
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
