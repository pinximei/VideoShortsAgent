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


# Agent 的系统提示词 —— 定义 Agent 的角色和行为规则
# system prompt 基础部分（Skills 索引由 SkillRegistry 动态生成）
SYSTEM_PROMPT_BASE = (
    "你是一个专业的短视频剪辑 Agent。\n\n"
    "你的任务是将用户提供的长视频，自动加工成有吸引力的短视频切片。\n\n"
    "注意事项：\n"
    "- 每一步完成后，检查结果是否合理再进行下一步\n"
    "- 如果某一步失败，尝试分析原因并决定是否重试\n"
    "- 所有中间文件都保存在任务目录中\n"
    "- 任务完成后，给用户一个清晰的总结\n"
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
        # 5. 将 Skills 也注册到 ToolRegistry（让 LLM 通过 tool_calls 发现）
        self.skill_registry.register_as_tools(self.tools)

        print("\n[Agent] 初始化完成 ✓")

    def _register_tools(self):
        """将三个 Skill 注册为 Agent 可用的工具

        每个工具需要：
        - name: 英文名称（LLM 通过它来调用）
        - description: 功能描述（LLM 据此判断何时使用）
        - parameters: 参数说明
        - func: 实际执行的函数
        """
        # 保存任务目录引用，供工具闭包使用
        self._task_dir = None
        self._video_path = None

        self.tools.add(
            name="transcribe",
            description="将视频/音频中的语音转为带时间戳的文字。输入视频路径，输出 transcript.json 的路径。",
            parameters={
                "video_path": "要转录的视频文件路径"
            },
            func=self._tool_transcribe
        )

        self.tools.add(
            name="render",
            description="将视频中的指定片段裁剪出来，并添加字幕，生成短视频。需要提供原始视频路径和分析结果。",
            parameters={
                "video_path": "原始视频文件路径",
                "start": "片段开始时间（秒）",
                "end": "片段结束时间（秒）",
                "hook_text": "要叠加的字幕文案"
            },
            func=self._tool_render
        )

    # ========== 工具实现（桥接 Skill） ==========

    def _tool_transcribe(self, video_path: str) -> str:
        """转录工具"""
        result_path = self.transcribe_skill.execute(video_path, self._task_dir)
        return f"转录完成，结果保存在: {result_path}"

    def _tool_analyze(self, transcript_path: str) -> str:
        """分析工具"""
        result = self.analysis_skill.execute(transcript_path)
        return json.dumps(result, ensure_ascii=False)

    def _tool_render(self, video_path: str, start: str, end: str, hook_text: str) -> str:
        """渲染工具"""
        analysis = {
            "start": float(start),
            "end": float(end),
            "hook_text": hook_text
        }
        output_path = self.render_skill.execute(video_path, analysis, self._task_dir)
        return f"渲染完成，输出文件: {output_path}"

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

                    # 检查是否是 Skill（LLM 可能通过 tool_calls 调用已注册的 Skill）
                    if func_name in self.skill_registry.names:
                        if self.skill_registry.should_inject_doc(func_name):
                            # ===== 首次调用：注入完整文档，不执行 =====
                            full_doc = self.skill_registry.get_full_doc(func_name)
                            tool_result = (
                                f"注意：{func_name} 是一个技能（Skill），不是工具（Tool）。"
                                f"以下是该技能的完整文档，请阅读后重新调用：\n\n{full_doc}"
                            )
                            print(f"\n  📘 首次调用 Skill: {func_name}")
                            print(f"     已注入完整文档，要求 LLM 阅读后重新调用")
                        else:
                            # ===== 再次调用：已读过文档，执行 executor =====
                            print(f"\n  📘 再次调用 Skill: {func_name}，执行 executor")
                            tool_result = self.skill_registry.execute(func_name, func_args, self._skill_context)
                            print(f"     执行结果: {tool_result[:200]}")

                        result["steps"].append({
                            "iteration": iteration,
                            "skill": func_name,
                            "args": func_args,
                            "mode": "skills"
                        })
                    else:
                        # 正常工具执行
                        tool_result = self.tools.call(func_name, func_args)
                        print(f"     结果: {tool_result[:200]}...")

                        result["steps"].append({
                            "iteration": iteration,
                            "tool": func_name,
                            "args": func_args,
                            "mode": "tool"
                        })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
            else:
                reply_text = assistant_message.content or ""
                messages.append({"role": "assistant", "content": reply_text})

                # ========== 通用 Skills 检测 ==========
                skill_call = self.skill_registry.parse_skill_call(reply_text)
                if skill_call:
                    skill_name = skill_call["name"]
                    skill_args = skill_call["args"]

                    if "error" in skill_call:
                        messages.append({"role": "user", "content": skill_call["error"]})
                        print(f"\n  📘 Skill 调用失败: {skill_call['error']}")
                        continue

                    print(f"\n  📘 检测到 Skill 调用: {skill_name}")
                    print(f"     参数: {skill_args}")

                    if self.skill_registry.should_inject_doc(skill_name):
                        # ===== 首次调用：注入完整文档，不执行 =====
                        full_doc = self.skill_registry.get_full_doc(skill_name)
                        messages.append({"role": "user", "content": (
                            f"收到。以下是 {skill_name} 技能的完整文档，请阅读后重新按格式调用：\n\n{full_doc}"
                        )})
                        print(f"     首次调用，已注入完整文档，等待 LLM 阅读后重新调用")
                    else:
                        # ===== 再次调用：已读过文档，执行 executor =====
                        print(f"     执行 {skill_name} executor...")
                        skill_result = self.skill_registry.execute(skill_name, skill_args, self._skill_context)
                        messages.append({"role": "user", "content": f"{skill_name} 技能执行完成，结果：\n{skill_result}"})
                        print(f"     结果: {skill_result[:200]}")

                    result["steps"].append({
                        "iteration": iteration,
                        "skill": skill_name,
                        "args": skill_args,
                        "mode": "skills"
                    })
                    continue

                # 没有 Skill 也没有 Tool → 任务完成
                print(f"\n  💬 Agent 最终回复: {reply_text}")
                result["status"] = "success"
                result["reply"] = reply_text
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
