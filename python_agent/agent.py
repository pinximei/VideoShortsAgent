"""
VideoShortsAgent - 真正的 ReAct Agent

这是一个 LLM 驱动的 Agent，使用 Qwen-Max 作为"大脑"，
自主决定何时调用哪个工具，而不是按固定顺序执行。

核心概念：
- ReAct 模式：Reasoning + Acting（思考 + 行动）
  1. LLM 思考当前状态，决定下一步做什么
  2. LLM 选择调用某个工具（Tool Call）
  3. 工具返回结果，LLM 观察结果
  4. LLM 继续思考，直到任务完成

- Function Calling：LLM 的 API 支持返回结构化的"工具调用"指令，
  而不仅仅是文字回复。这让 Agent 能可靠地与外部工具交互。

使用示例：
    agent = VideoShortsAgent(api_key="sk-xxx")
    result = agent.run("帮我把这个视频做成短视频", video_path="input.mp4")
"""
import os
import uuid
import json
from datetime import datetime
from openai import OpenAI

from python_agent.tools import ToolRegistry
from python_agent.skills.transcribe_skill import TranscribeSkill
from python_agent.skills.analysis_skill import AnalysisSkill
from python_agent.skills.render_skill import RenderSkill


# Agent 的系统提示词 —— 定义 Agent 的角色和行为规则
SYSTEM_PROMPT = """你是一个专业的短视频剪辑 Agent。

你的任务是将用户提供的长视频，自动加工成有吸引力的短视频切片。

你有以下工具可以使用：
1. transcribe - 将视频中的语音转为文字（带时间戳）
2. analyze - 从文字中找出最有"爆款潜力"的金句片段
3. render - 将选中的片段裁剪并添加字幕，生成短视频

工作流程建议（但你可以根据实际情况灵活调整）：
1. 先用 transcribe 获取视频的文字内容
2. 再用 analyze 找出金句
3. 最后用 render 生成短视频

注意事项：
- 每一步完成后，检查结果是否合理再进行下一步
- 如果某一步失败，尝试分析原因并决定是否重试
- 所有中间文件都保存在任务目录中
- 任务完成后，给用户一个清晰的总结
"""

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

    def __init__(self, api_key: str, llm_model: str = "qwen3", whisper_model: str = "base"):
        """初始化 Agent

        Args:
            api_key: DashScope API Key
            llm_model: Qwen 模型名称（如 qwen-max / qwen-plus / qwen-turbo）
            whisper_model: Whisper 模型大小
        """
        print("=" * 60)
        print("  VideoShortsAgent (ReAct) 初始化中...")
        print("=" * 60)

        # 1. 初始化 LLM 客户端（Agent 的"大脑"）
        self.llm = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.llm_model = llm_model

        # 2. 初始化 Skills
        self.transcribe_skill = TranscribeSkill(model_path=whisper_model)
        self.analysis_skill = AnalysisSkill(api_key=api_key, model=llm_model)
        self.render_skill = RenderSkill()

        # 3. 注册工具（把 Skill 包装成 LLM 可调用的 Tool）
        self.tools = ToolRegistry()
        self._register_tools()

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
            name="analyze",
            description="分析转录文本，找出最有爆款潜力的15-30秒金句片段。输入 transcript.json 路径，输出包含 start、end、hook_text 的分析结果。",
            parameters={
                "transcript_path": "transcript.json 文件路径"
            },
            func=self._tool_analyze
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

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_message}
        ]

        # 3. ReAct 循环
        result = {"task_id": task_id, "status": "running", "steps": []}

        for iteration in range(1, MAX_ITERATIONS + 1):
            print(f"\n--- ReAct 迭代 {iteration}/{MAX_ITERATIONS} ---")

            # 3a. 调用 LLM（思考 + 决策）
            response = self.llm.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                tools=self.tools.get_schemas(),  # 告诉 LLM 有哪些工具可用
                tool_choice="auto"               # 让 LLM 自己决定是否调用工具
            )

            assistant_message = response.choices[0].message

            # 3b. 检查 LLM 是否选择调用工具
            if assistant_message.tool_calls:
                # LLM 决定调用工具 → 执行 Action
                # 先将 assistant 的消息加入历史
                messages.append(assistant_message.model_dump())

                for tool_call in assistant_message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    print(f"  🔧 调用工具: {func_name}")
                    print(f"     参数: {func_args}")

                    # 执行工具
                    tool_result = self.tools.call(func_name, func_args)

                    print(f"     结果: {tool_result[:200]}...")  # 截断显示

                    # 记录步骤
                    result["steps"].append({
                        "iteration": iteration,
                        "tool": func_name,
                        "args": func_args,
                        "result": tool_result
                    })

                    # 将工具结果反馈给 LLM（这就是"观察"环节）
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
            else:
                # LLM 没有调用工具 → 认为任务完成，给出最终回复
                final_reply = assistant_message.content
                print(f"\n  💬 Agent 回复: {final_reply}")

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
