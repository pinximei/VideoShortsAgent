"""
VideoShortsAgent - ReAct Agent 实现

基于 ReAct（Reasoning + Acting）模式的 AI Agent。
LLM 自主思考并决定何时调用哪个工具（Tool Calling），完成视频短片制作。

使用示例：
    agent = VideoShortsAgent(api_key="sk-xxx")
    result = agent.run("帮我把这个视频做成短视频", video_path="./video.mp4")
"""
import os
import json
import uuid
from datetime import datetime
from openai import OpenAI

from python_agent.tools import ToolRegistry
from python_agent.skills.transcribe_skill import TranscribeSkill
from python_agent.skills.analysis_skill import AnalysisSkill
from python_agent.skills.render_skill import RenderSkill
from python_agent.skills.download_skill import DownloadSkill
from python_agent.skills.dubbing_skill import DubbingSkill

EFFECTS_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "remotion_effects", "effects_config.json"
)


def _load_effects_config() -> dict:
    """加载特效配置文件"""
    try:
        with open(EFFECTS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def build_system_prompt() -> str:
    """动态构建 System Prompt，特效描述从 effects_config.json 加载"""
    config = _load_effects_config()

    # 构建特效描述
    effects_lines = []

    # 字幕风格
    caption_styles = config.get("caption_styles", {})
    if caption_styles:
        styles_desc = " / ".join(
            f"'{k}'（{v}）" for k, v in caption_styles.items()
        )
        effects_lines.append(f"- caption_style: 字幕动画风格，可选 {styles_desc}")

    # 覆盖层
    overlays = config.get("overlays", {})
    if "gradient" in overlays:
        g = overlays["gradient"]
        effects_lines.append(f"- gradient: true/false，{g.get('description', '渐变背景氛围层')}")
        colors = g.get("default_colors", ["#FF6B6B", "#4ECDC4"])
        effects_lines.append(f"- gradient_colors: [颜色1, 颜色2]，渐变色，默认 {colors}")

    # 转场
    transitions = config.get("transitions", {})
    if transitions:
        trans_desc = " / ".join(
            f"'{k}'（{v}）" for k, v in transitions.items()
        )
        effects_lines.append(f"- transition: 片段间转场效果，可选 {trans_desc}")
    effects_lines.append("- transition_duration: 转场时长（秒），默认 0.5")

    # 预设
    presets = config.get("presets", {})
    presets_desc = ""
    if presets:
        preset_items = []
        for name, preset in presets.items():
            preset_items.append(f"  - {name}风格: {json.dumps(preset, ensure_ascii=False)}")
        presets_desc = (
            "\n风格预设（可直接使用，也可自由组合）：\n"
            + "\n".join(preset_items) + "\n"
        )

    effects_section = "\n".join(effects_lines)

    return (
        "你是一个专业的短视频剪辑 Agent。\n\n"
        "你的任务是将用户提供的长视频，自动加工成有吸引力的短视频切片。\n\n"
        "标准流程：\n"
        "0. 如果用户提供的是 URL，先使用 download 下载视频\n"
        "1. 使用 transcribe 将视频语音转为文字（会自动检测语言）\n"
        "2. 使用 analyze 理解视频全部内容，浓缩为若干关键段落，完整描述主题（返回 clips 数组，每个含 tts_text）\n"
        "3. 使用 dubbing 工具生成 TTS 配音（所有语言都需要，analyze 会返回 tts_text）\n"
        "   - 【重要】dubbing 返回的完整 JSON 字符串，必须原样传给 render 的 tts_info_json 参数\n"
        "   - 根据视频内容风格选择合适的语音角色（通过 voice 参数）\n"
        "4. 使用 render 渲染最终视频\n"
        "   - 【重要】video_path 永远使用原始视频（source_video），不要使用任何中间文件\n"
        "   - dubbing 不产出视频文件，只产出 TTS 音频信息\n"
        "   - render 的 tts_info_json 填入 dubbing 返回的完整 JSON 字符串\n"
        "   - TTS 时长决定画面时长，视频画面适配语音\n"
        "   - 【重要】根据视频内容风格，自动选择最合适的特效组合（通过 effects_json 参数）\n\n"
        f"可用特效（通过 render 的 effects_json 参数指定）：\n{effects_section}\n"
        f"{presets_desc}\n"
        "可用语音角色（通过 dubbing 的 voice 参数指定）：\n"
        "- zh-CN-YunyangNeural: 男声，专业播音腔，适合新闻/科技/严肃内容\n"
        "- zh-CN-YunjianNeural: 男声，充满激情，适合体育/励志/热血内容\n"
        "- zh-CN-YunxiNeural: 男声，阳光活泼，适合日常/休闲/故事类内容\n"
        "- zh-CN-XiaoxiaoNeural: 女声，温暖自然，适合生活/情感/教育内容\n"
        "- zh-CN-XiaoyiNeural: 女声，活泼可爱，适合卡通/娱乐/轻松内容\n\n"
        "注意事项：\n"
        "- render 的 analysis_json 直接填入 analyze 返回的完整 JSON 字符串\n"
        "- 根据视频内容风格，主动选择最匹配的特效预设或自由组合特效参数\n"
        "- 每一步完成后检查结果是否合理再进行下一步\n"
        "- 任务完成后给用户一个清晰的总结\n"
    )

# ReAct 循环的最大轮次
MAX_ITERATIONS = 10


class VideoShortsAgent:
    """ReAct Agent - LLM 驱动的短视频加工 Agent"""

    def __init__(self, api_key: str, llm_model: str = "qwen3.5-flash",
                 whisper_model: str = "base", transcribe_mode: str = "local",
                 groq_api_key: str = ""):
        """初始化 Agent

        Args:
            api_key: DashScope API Key
            llm_model: Qwen 模型名称
            whisper_model: Whisper 模型大小（local 模式）
            transcribe_mode: "local" 或 "groq"
            groq_api_key: Groq API Key（groq 模式）
        """
        print("=" * 60)
        print("  VideoShortsAgent (ReAct) 初始化中...")
        print("=" * 60)

        # 1. 初始化 LLM 客户端
        self.llm = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.llm_model = llm_model

        # 2. 初始化 Skills
        self.transcribe_skill = TranscribeSkill(
            model_path=whisper_model, mode=transcribe_mode,
            groq_api_key=groq_api_key
        )
        self.analysis_skill = AnalysisSkill(api_key=api_key, model=llm_model)
        self.render_skill = RenderSkill()
        self.download_skill = DownloadSkill()
        self.dubbing_skill = DubbingSkill()

        # 3. 注册 Tools
        self.tools = ToolRegistry()
        self._register_tools()

        print("\n[Agent] 初始化完成 ✓")

    def _register_tools(self):
        """注册所有工具"""
        self._task_dir = None
        self._video_path = None
        self._use_remotion = False

        self.tools.add(
            name="download",
            description="从 YouTube 等平台下载视频。输入 URL，返回下载后的本地文件路径。",
            parameters={"url": "视频 URL（YouTube、Bilibili 等）"},
            func=self._tool_download
        )

        self.tools.add(
            name="transcribe",
            description="将视频/音频中的语音转为带时间戳的文字，并自动检测语言。输入视频路径，输出 transcript.json 的路径和检测到的语言。",
            parameters={"video_path": "要转录的视频文件路径"},
            func=self._tool_transcribe
        )

        self.tools.add(
            name="analyze",
            description="从转录文本中分析内容并提取若干关键主题段落，返回 clips 数组，每个包含 start、end、hook_text。如果源语言是英文，还会返回 tts_text（中文配音文本）。",
            parameters={
                "transcript_path": "transcript.json 文件路径",
                "language": "（可选）源语言代码，如 'en'。如果 transcript.json 中已包含 language 信息则无需指定。用于旧格式的 transcript 文件。"
            },
            func=self._tool_analyze
        )

        self.tools.add(
            name="dubbing",
            description="为视频生成中文 TTS 配音音频。需要 analyze 返回的包含 tts_text 的结果。返回 TTS 信息 JSON（包含每个片段的音频路径和实际时长），需传给 render。可通过 voice 参数指定语音角色。",
            parameters={
                "analysis_json": "analyze 返回的完整 JSON 字符串，clips 中需含 tts_text 字段",
                "voice": "（可选）语音角色名称，如 'zh-CN-YunyangNeural'。不指定则使用默认语音。"
            },
            func=self._tool_dubbing
        )

        self.tools.add(
            name="render",
            description="根据分析结果渲染短视频。支持多片段裁剪+字幕+拼接。如果有 tts_info_json（来自 dubbing），会以 TTS 时长为主时钟。",
            parameters={
                "video_path": "原始视频文件路径",
                "analysis_json": "analyze 返回的完整 JSON 字符串，包含 clips 数组",
                "tts_info_json": "（可选）dubbing 返回的 TTS 信息 JSON。有此参数时，视频会静音并使用 TTS 音频。",
                "effects_json": "特效配置 JSON，如 {\"caption_style\":\"spring\",\"gradient\":true}。不传则使用默认 ASS 字幕。"
            },
            func=self._tool_render
        )

    # ========== 工具实现 ==========

    def _tool_download(self, url: str) -> str:
        output_path = self.download_skill.execute(url, self._task_dir)
        return f"下载完成，视频保存在: {output_path}"

    def _tool_transcribe(self, video_path: str) -> str:
        # 如果 transcript.json 已存在，跳过耗时的转录
        existing = os.path.join(self._task_dir, "transcript.json")
        if os.path.exists(existing):
            try:
                with open(existing, "r", encoding="utf-8") as f:
                    data = json.load(f)
                lang = data.get("language", "unknown") if isinstance(data, dict) else "unknown"
                print(f"[Agent] transcript.json 已存在，跳过转录，语言: {lang}")
                return f"转录文件已存在，跳过转录: {existing}\n检测到语言: {lang}"
            except Exception:
                pass  # 文件损坏，重新转录
        result_path, detected_lang = self.transcribe_skill.execute(video_path, self._task_dir)
        return f"转录完成，结果保存在: {result_path}\n检测到语言: {detected_lang}"

    def _tool_analyze(self, transcript_path: str, language: str = "") -> str:
        # 如果用户指定了语言且 transcript 是旧格式，需要注入 language
        if language:
            with open(transcript_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                # 旧格式：升级为新格式并写回
                upgraded = {"language": language, "language_probability": 1.0, "segments": data}
                with open(transcript_path, "w", encoding="utf-8") as f:
                    json.dump(upgraded, f, ensure_ascii=False, indent=2)
                print(f"[Agent] 已将旧格式 transcript 升级为新格式，语言设为: {language}")
        result = self.analysis_skill.execute(transcript_path)
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _tool_dubbing(self, analysis_json: str, voice: str = "") -> str:
        try:
            analysis = json.loads(analysis_json)
        except json.JSONDecodeError:
            return f"错误：analysis_json 不是合法的 JSON: {analysis_json[:200]}"
        result = self.dubbing_skill.execute(analysis, self._task_dir, voice=voice)
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _tool_render(self, video_path: str, analysis_json: str,
                     tts_info_json: str = "", effects_json: str = "") -> str:
        try:
            analysis = json.loads(analysis_json)
        except json.JSONDecodeError:
            return f"错误：analysis_json 不是合法的 JSON: {analysis_json[:200]}"
        effects = None
        if effects_json:
            try:
                effects = json.loads(effects_json)
            except json.JSONDecodeError:
                pass
        tts_info = None
        if tts_info_json:
            try:
                tts_info = json.loads(tts_info_json)
            except json.JSONDecodeError:
                pass
        # 注入渲染模式到 effects
        if effects is None:
            effects = {}
        effects["use_remotion"] = self._use_remotion
        # 强制使用原始视频路径（不信任 LLM 传入的 video_path）
        actual_video_path = video_path
        if self._video_path and os.path.exists(self._video_path):
            if os.path.abspath(video_path) != os.path.abspath(self._video_path):
                print(f"[Agent] ⚠️ video_path 被覆盖: {video_path} → {self._video_path}")
            actual_video_path = self._video_path
        output_path = self.render_skill.execute(
            actual_video_path, analysis, self._task_dir, effects=effects, tts_info=tts_info
        )
        return f"渲染完成，输出文件: {output_path}"

    # ========== ReAct 主循环 ==========

    def run(self, user_message: str, video_path: str = None, output_base: str = "output",
            task_dir: str = None, use_remotion: bool = False) -> dict:
        """执行 Agent 的 ReAct 循环

        Args:
            user_message: 用户的指令
            video_path: 视频文件路径（可选）
            output_base: 输出根目录
            task_dir: 已有任务目录路径（可选），用于复用之前的转录结果
            use_remotion: 是否使用 Remotion 特效渲染（否则使用 FFmpeg ASS 字幕）

        Returns:
            包含任务结果的字典
        """
        self._use_remotion = use_remotion
        # 1. 创建或复用任务目录
        if task_dir and os.path.isdir(task_dir):
            self._task_dir = os.path.abspath(task_dir)
            task_id = os.path.basename(task_dir).replace("task_", "") or uuid.uuid4().hex[:8]
        else:
            task_id = uuid.uuid4().hex[:8]
            self._task_dir = os.path.abspath(os.path.join(output_base, f"task_{task_id}"))
        self._video_path = video_path
        os.makedirs(self._task_dir, exist_ok=True)

        print("\n" + "=" * 60)
        print(f"  🎬 新任务: {task_id}")
        print(f"  💬 用户指令: {user_message}")
        if video_path:
            print(f"  📁 视频: {video_path}")
        print(f"  🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # 2. 构建初始消息列表
        if video_path:
            full_message = f"{user_message}\n\n视频文件路径: {video_path}\n任务工作目录: {self._task_dir}"
        else:
            full_message = user_message

        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": full_message}
        ]

        # 3. ReAct 循环
        result = {"task_id": task_id, "steps": [], "status": "running", "reply": ""}

        # 创建调试日志目录
        debug_dir = os.path.join(self._task_dir, "llm_debug")
        os.makedirs(debug_dir, exist_ok=True)

        for iteration in range(1, MAX_ITERATIONS + 1):
            print(f"\n{'='*60}")
            print(f"  📍 [EVENT] iteration_start | iteration={iteration}/{MAX_ITERATIONS}")
            print(f"{'='*60}")

            # 保存 LLM 输入
            input_log = os.path.join(debug_dir, f"call_{iteration}_input.json")
            with open(input_log, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)

            # === 生命周期事件：LLM 调用前 ===
            print(f"  📍 [EVENT] llm_call_start | model={self.llm_model}")
            print(f"     messages_count={len(messages)}, tools_count={len(self.tools.get_schemas())}")

            # 调用 LLM
            response = self.llm.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                tools=self.tools.get_schemas(),
            )
            assistant_message = response.choices[0].message
            choice = response.choices[0]

            # === 生命周期事件：LLM 调用后 ===
            usage = response.usage
            print(f"  📍 [EVENT] llm_call_end")
            print(f"     finish_reason={choice.finish_reason}")
            print(f"     has_tool_calls={bool(assistant_message.tool_calls)}")
            print(f"     content_length={len(assistant_message.content) if assistant_message.content else 0}")
            if hasattr(assistant_message, 'reasoning_content') and assistant_message.reasoning_content:
                print(f"     reasoning_content_length={len(assistant_message.reasoning_content)}")
            if usage:
                print(f"     tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")

            # 保存 LLM 输出（含完整事件数据）
            output_log = os.path.join(debug_dir, f"call_{iteration}_output.json")
            try:
                output_data = response.model_dump()
            except Exception:
                output_data = {"content": assistant_message.content}
            with open(output_log, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"     logs: {input_log} / {output_log}")

            # 处理响应
            if assistant_message.tool_calls:
                messages.append(assistant_message.model_dump())

                for tool_call in assistant_message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    # === 生命周期事件：工具执行前 ===
                    print(f"\n  📍 [EVENT] tool_call_start | tool={func_name}")
                    print(f"     call_id={tool_call.id}")
                    print(f"     args={func_args}")

                    tool_result = self.tools.call(func_name, func_args)

                    # === 生命周期事件：工具执行后 ===
                    print(f"  📍 [EVENT] tool_call_end | tool={func_name}")
                    print(f"     result_length={len(tool_result)}")
                    print(f"     result_preview={tool_result[:200]}")

                    result["steps"].append({
                        "iteration": iteration,
                        "tool": func_name,
                        "args": func_args,
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
            else:
                final_reply = assistant_message.content
                # === 生命周期事件：任务完成 ===
                print(f"\n  📍 [EVENT] task_complete | status=success")
                print(f"     reply_length={len(final_reply) if final_reply else 0}")
                print(f"     reply_preview={final_reply[:200] if final_reply else ''}")

                result["status"] = "success"
                result["reply"] = final_reply
                break
        else:
            # === 生命周期事件：超时 ===
            print(f"\n  📍 [EVENT] task_timeout | max_iterations={MAX_ITERATIONS}")
            result["status"] = "max_iterations"
            result["reply"] = "达到最大迭代次数，任务可能未完全完成。"

        print(f"\n{'='*60}")
        print(f"  📍 [EVENT] task_end | task_id={task_id} | status={result['status']}")
        print(f"     total_steps={len(result['steps'])}")
        print(f"{'='*60}")

        return result
