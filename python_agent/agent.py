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
from python_agent.llm_client import create_llm_client
from python_agent.config import get_config

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


PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt(filename: str) -> str:
    """加载提示词文件"""
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


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

    effects_section = "可用特效（通过 render 的 effects_json 参数指定）：\n" + "\n".join(effects_lines) if effects_lines else ""

    # 预设
    presets = config.get("presets", {})
    presets_section = ""
    if presets:
        preset_items = []
        for name, preset in presets.items():
            preset_items.append(f"  - {name}风格: {json.dumps(preset, ensure_ascii=False)}")
        presets_section = (
            "\n风格预设（可直接使用，也可自由组合）：\n"
            + "\n".join(preset_items) + "\n"
        )

    # 读取模板并填充
    template = _load_prompt("agent_system.txt")
    return template.format(
        effects_section=effects_section,
        presets_section=presets_section
    )

# ReAct 循环的最大轮次（从 Config 读取）


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

        # 1. 初始化 LLM 客户端（从 Config 读取 provider 配置）
        self.llm = create_llm_client(api_key=api_key)
        self.llm_model = llm_model or get_config().llm_model

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

        max_iter = get_config().max_iterations
        for iteration in range(1, max_iter + 1):
            print(f"\n--- 🔄 迭代 {iteration}/{max_iter} ---")

            # 调用 LLM
            response = self.llm.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                tools=self.tools.get_schemas(),
            )
            assistant_message = response.choices[0].message
            choice = response.choices[0]

            # 处理响应
            if assistant_message.tool_calls:
                messages.append(assistant_message.model_dump())

                for tool_call in assistant_message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    print(f"  🔧 {func_name}({func_args})")
                    tool_result = self.tools.call(func_name, func_args)
                    print(f"  ✅ {func_name} → {tool_result[:100]}")

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
                print(f"\n✅ Agent 任务完成")

                result["status"] = "success"
                result["reply"] = final_reply
                break
        else:
            print(f"\n⚠️ 达到最大迭代次数 ({max_iter})")
            result["status"] = "max_iterations"
            result["reply"] = "达到最大迭代次数，任务可能未完全完成。"

        print(f"\n[Agent] 任务 {task_id} 结束 | 状态={result['status']} | 步骤={len(result['steps'])}")

        return result
