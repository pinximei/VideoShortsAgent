"""
VideoShortsAgent - ReAct Agent 实现

这是一个基于 ReAct（Reasoning + Acting）模式的 AI Agent。
支持两种能力调用方式：
- Tool Calling：通过 API tools 参数结构化调用（如 transcribe、render）
- Skills：通过 system prompt 注入索引 + [USE_SKILL] 文本调用（如 analyze）

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
from python_agent.skill_registry import SkillRegistry
from python_agent.skills.transcribe_skill import TranscribeSkill
from python_agent.skills.analysis_skill import AnalysisSkill
from python_agent.skills.render_skill import RenderSkill


# Agent 的系统提示词基础部分，Skills 索引由 SkillRegistry 动态拼接
SYSTEM_PROMPT_BASE = (
    "你是一个专业的短视频剪辑 Agent。\n\n"
    "你的任务是将用户提供的长视频，自动加工成有吸引力的短视频切片。\n\n"
    "注意事项：\n"
    "- 每一步完成后，检查结果是否合理再进行下一步\n"
    "- 如果某一步失败，尝试分析原因并决定是否重试\n"
    "- 所有中间文件都保存在任务目录中\n"
    "- 任务完成后，给用户一个清晰的总结\n"
    "\n"
    "技能（Skills）使用流程：\n"
    "1. 首先，使用 `read_skill` 工具阅读你想要使用的技能的完整文档，了解其功能、输入和输出。\n"
    "2. 然后，根据 `read_skill` 返回的文档，使用 `execute_skill` 工具执行该技能，并传入正确的 JSON 格式参数。\n"
    "3. 技能执行结果将作为 `execute_skill` 工具的输出返回给你。\n"
)

# ReAct 循环的最大轮次（防止无限循环）
MAX_ITERATIONS = 10


class VideoShortsAgent:
    """ReAct Agent - LLM 驱动的短视频加工 Agent

    与之前的 Pipeline 版本的关键区别：
    - Pipeline：代码写死执行顺序（1→2→3）
    - Agent：LLM 自主思考并决定下一步做什么

    这意味着 Agent 可以：
    - 根据转录结果判断是否需要换模型重试
    - 根据分析结果决定是否需要调整参数
    - 出错时自主决定重试策略
    """

    def __init__(self, api_key: str, llm_model: str = "qwen3.5-flash", whisper_model: str = "base"):
        """初始化 Agent

        Args:
            api_key: DashScope API Key
            llm_model: Qwen 模型名称
            whisper_model: Whisper 模型大小
        """
        print("=" * 60)
        print("  VideoShortsAgent (ReAct) 初始化中...")
        print("=" * 60)

        # 保存上下文（传递给 Skill executor）
        self._api_key = api_key
        self._skill_context = {"api_key": api_key, "model": llm_model}

        # 1. 初始化 LLM 客户端
        self.llm = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.llm_model = llm_model

        # 2. 初始化 Tool 对应的 Skills
        self.transcribe_skill = TranscribeSkill(model_path=whisper_model)
        self.render_skill = RenderSkill()

        # 3. 发现并注册 Skills（通用框架）
        self.skill_registry = SkillRegistry(os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills"))

        # 4. 注册 Tools（结构化调用）
        self.tools = ToolRegistry()
        self._register_tools()

        print("\n[Agent] 初始化完成 ✓")

    def _register_tools(self):
        """注册所有工具（包括 Skill 操作工具）"""
        self._task_dir = None
        self._video_path = None

        # ===== 业务工具 =====
        self.tools.add(
            name="transcribe",
            description="将视频/音频中的语音转为带时间戳的文字。输入视频路径，输出 transcript.json 的路径。",
            parameters={"video_path": "要转录的视频文件路径"},
            func=self._tool_transcribe
        )

        self.tools.add(
            name="render",
            description="将视频中的指定片段裁剪出来并添加字幕，生成短视频。",
            parameters={
                "video_path": "原始视频文件路径",
                "start": "片段开始时间（秒）",
                "end": "片段结束时间（秒）",
                "hook_text": "要叠加的字幕文案"
            },
            func=self._tool_render
        )

        # ===== Skill 操作工具（通用） =====
        self.tools.add(
            name="read_skill",
            description="读取指定技能（Skill）的完整文档。在使用某个技能之前，必须先调用此工具阅读文档，了解其输入输出格式。",
            parameters={"skill_name": "要读取的技能名称"},
            func=self._tool_read_skill
        )

        self.tools.add(
            name="execute_skill",
            description="执行指定的技能（Skill）。必须先用 read_skill 阅读文档后才能调用。参数以 JSON 字符串传递。",
            parameters={
                "skill_name": "要执行的技能名称",
                "arguments": "技能参数，JSON 字符串格式，具体参数请参考 read_skill 返回的文档"
            },
            func=self._tool_execute_skill
        )

    # ========== 工具实现 ==========

    def _tool_transcribe(self, video_path: str) -> str:
        result_path = self.transcribe_skill.execute(video_path, self._task_dir)
        return f"转录完成，结果保存在: {result_path}"

    def _tool_render(self, video_path: str, start: str, end: str, hook_text: str) -> str:
        analysis = {
            "start": float(start),
            "end": float(end),
            "hook_text": hook_text
        }
        output_path = self.render_skill.execute(video_path, analysis, self._task_dir)
        return f"渲染完成，输出文件: {output_path}"

    def _tool_read_skill(self, skill_name: str) -> str:
        """读取 Skill 完整文档"""
        doc = self.skill_registry.get_full_doc(skill_name)
        print(f"  📄 已加载 Skill 文档: {skill_name}")
        return doc

    def _tool_execute_skill(self, skill_name: str, arguments: str) -> str:
        """执行 Skill"""
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError:
            return f"错误：arguments 不是合法的 JSON 字符串: {arguments}"
        print(f"  ⚡ 执行 Skill: {skill_name}，参数: {args}")
        return self.skill_registry.execute(skill_name, args, self._skill_context)

    # ========== ReAct 主循环 ==========

    def run(self, user_message: str, video_path: str = None, output_base: str = "output") -> dict:
        """执行 Agent 的 ReAct 循环

        Args:
            user_message: 用户的指令（如 "帮我把这个视频做成短视频"）
            video_path: 视频文件路径（可选，也可以在 user_message 中指定）
            output_base: 输出根目录

        Returns:
            包含任务结果的字典
        """
        # 1. 创建任务目录
        task_id = uuid.uuid4().hex[:8]
        self._task_dir = os.path.join(output_base, f"task_{task_id}")
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
        #    messages 是 LLM 的"记忆"，记录了整个对话过程
        if video_path:
            full_message = f"{user_message}\n\n视频文件路径: {video_path}\n任务工作目录: {self._task_dir}"
        else:
            full_message = user_message

        # 动态生成 system prompt = 基础 + Skills 索引
        system_prompt = SYSTEM_PROMPT_BASE + "\n" + self.skill_registry.get_index()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_message}
        ]

        # 3. ReAct 循环
        result = {"task_id": task_id, "status": "running", "steps": []}
        llm_call_count = 0  # 记录 LLM 调用次数

        for iteration in range(1, MAX_ITERATIONS + 1):
            print(f"\n--- ReAct 迭代 {iteration}/{MAX_ITERATIONS} ---")

            # ========== 保存 LLM 完整输入为 JSON 文件 ==========
            llm_call_count += 1
            debug_dir = os.path.join(self._task_dir, "llm_debug")
            os.makedirs(debug_dir, exist_ok=True)

            # 保存输入
            llm_input = {
                "_说明": f"这是第 {llm_call_count} 次 LLM API 调用的完整输入参数",
                "model": self.llm_model,
                "tool_choice": "auto",
                "messages": messages,
                "tools": self.tools.get_schemas()
            }
            input_file = os.path.join(debug_dir, f"call_{llm_call_count}_input.json")
            with open(input_file, "w", encoding="utf-8") as f:
                json.dump(llm_input, f, ensure_ascii=False, indent=2)
            print(f"  📤 输入已保存: {input_file}")

            # 3a. 调用 LLM（思考 + 决策）
            response = self.llm.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                tools=self.tools.get_schemas(),
                tool_choice="auto"
            )

            assistant_message = response.choices[0].message
            usage = response.usage

            # ========== 保存 LLM 完整输出为 JSON 文件 ==========
            llm_output = {
                "_说明": f"这是第 {llm_call_count} 次 LLM API 调用的完整响应",
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else None,
                    "completion_tokens": usage.completion_tokens if usage else None,
                    "total_tokens": usage.total_tokens if usage else None
                },
                "message": assistant_message.model_dump()
            }
            output_file = os.path.join(debug_dir, f"call_{llm_call_count}_output.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(llm_output, f, ensure_ascii=False, indent=2)

            # 终端简要提示
            tokens = f"{usage.total_tokens}t" if usage else "?"
            if assistant_message.tool_calls:
                tools_called = [tc.function.name for tc in assistant_message.tool_calls]
                print(f"  📥 输出已保存: {output_file}  ({tokens}, 调用工具: {tools_called})")
            else:
                print(f"  📥 输出已保存: {output_file}  ({tokens}, 直接回复)")

            # 3b. 检查 LLM 是否选择调用工具
            if assistant_message.tool_calls:
                # LLM 决定调用工具 → 执行 Action
                messages.append(assistant_message.model_dump())

                for tool_call in assistant_message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    print(f"\n  🔧 执行工具: {func_name}")
                    print(f"     参数: {func_args}")

                    # 统一通过 ToolRegistry 执行（含 read_skill、execute_skill）
                    tool_result = self.tools.call(func_name, func_args)
                    print(f"     结果: {tool_result[:200]}...")

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
                # LLM 没有调用工具 → 任务完成
                final_reply = assistant_message.content
                print(f"\n  💬 Agent 最终回复: {final_reply}")

                result["status"] = "success"
                result["reply"] = final_reply
                break
        else:
            # 超过最大迭代次数
            result["status"] = "max_iterations"
            result["reply"] = "达到最大迭代次数，任务可能未完全完成。"

        print("\n" + "=" * 60)
        print(f"  {'✅' if result['status'] == 'success' else '⚠️'} 任务结束: {task_id}")
        print(f"  共执行 {len(result['steps'])} 个工具调用")
        print("=" * 60)

        return result
