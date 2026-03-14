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


SYSTEM_PROMPT = (
    "你是一个专业的短视频剪辑 Agent。\n\n"
    "你的任务是将用户提供的长视频，自动加工成有吸引力的短视频切片。\n\n"
    "标准流程：\n"
    "1. 使用 transcribe 将视频语音转为文字\n"
    "2. 使用 analyze 从转录文本中找出多个精彩片段（返回 clips 数组）\n"
    "3. 使用 render 渲染最终视频，传入 analyze 的结果 + 特效配置\n\n"
    "可用特效（通过 render 的 effects_json 参数指定）：\n"
    "- caption_style: 字幕动画风格，可选 'spring'（弹出）/ 'fade'（淡入）/ 'typewriter'（打字机）\n"
    "- gradient: true/false，是否叠加渐变背景氛围层\n"
    "- gradient_colors: [颜色1, 颜色2]，渐变色，如 ['#FF6B6B', '#4ECDC4']\n"
    "示例: {\"caption_style\": \"spring\", \"gradient\": true}\n\n"
    "注意事项：\n"
    "- render 的 analysis_json 直接填入 analyze 返回的完整 JSON 字符串\n"
    "- 根据视频内容风格主动选择合适的特效组合\n"
    "- 每一步完成后检查结果是否合理再进行下一步\n"
    "- 任务完成后给用户一个清晰的总结\n"
)

# ReAct 循环的最大轮次
MAX_ITERATIONS = 10


class VideoShortsAgent:
    """ReAct Agent - LLM 驱动的短视频加工 Agent"""

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

        # 1. 初始化 LLM 客户端
        self.llm = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.llm_model = llm_model

        # 2. 初始化 Skills
        self.transcribe_skill = TranscribeSkill(model_path=whisper_model)
        self.analysis_skill = AnalysisSkill(api_key=api_key, model=llm_model)
        self.render_skill = RenderSkill()

        # 3. 注册 Tools
        self.tools = ToolRegistry()
        self._register_tools()

        print("\n[Agent] 初始化完成 ✓")

    def _register_tools(self):
        """注册所有工具"""
        self._task_dir = None
        self._video_path = None

        self.tools.add(
            name="transcribe",
            description="将视频/音频中的语音转为带时间戳的文字。输入视频路径，输出 transcript.json 的路径。",
            parameters={"video_path": "要转录的视频文件路径"},
            func=self._tool_transcribe
        )

        self.tools.add(
            name="analyze",
            description="从转录文本中分析并提取多个精彩片段（3-5个），返回 clips 数组，每个包含 start、end、hook_text。",
            parameters={"transcript_path": "transcript.json 文件路径"},
            func=self._tool_analyze
        )

        self.tools.add(
            name="render",
            description="根据分析结果渲染短视频。支持多片段裁剪+字幕+拼接。可通过 effects_json 启用 Remotion 特效。",
            parameters={
                "video_path": "原始视频文件路径",
                "analysis_json": "analyze 返回的完整 JSON 字符串，包含 clips 数组",
                "effects_json": "特效配置 JSON，如 {\"caption_style\":\"spring\",\"gradient\":true}。不传则使用默认 ASS 字幕。"
            },
            func=self._tool_render
        )

    # ========== 工具实现 ==========

    def _tool_transcribe(self, video_path: str) -> str:
        result_path = self.transcribe_skill.execute(video_path, self._task_dir)
        return f"转录完成，结果保存在: {result_path}"

    def _tool_analyze(self, transcript_path: str) -> str:
        result = self.analysis_skill.execute(transcript_path)
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _tool_render(self, video_path: str, analysis_json: str, effects_json: str = "") -> str:
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
        output_path = self.render_skill.execute(video_path, analysis, self._task_dir, effects=effects)
        return f"渲染完成，输出文件: {output_path}"

    # ========== ReAct 主循环 ==========

    def run(self, user_message: str, video_path: str = None, output_base: str = "output") -> dict:
        """执行 Agent 的 ReAct 循环

        Args:
            user_message: 用户的指令
            video_path: 视频文件路径（可选）
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
        if video_path:
            full_message = f"{user_message}\n\n视频文件路径: {video_path}\n任务工作目录: {self._task_dir}"
        else:
            full_message = user_message

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
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
