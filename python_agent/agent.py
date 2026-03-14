"""
VideoShortsAgent - 纯 Python Agent 编排器

这是整个流水线的"大脑"，负责按顺序调用三个 Skill，
将长视频加工成短视频切片。

核心概念：
- Agent：一个自动化的任务协调者，按预定义的工作流串联各个能力
- Skill：具体的能力单元（转录、分析、渲染）
- Pipeline：技能按序执行的流水线

工作流程：
    输入视频 → TranscribeSkill → AnalysisSkill → RenderSkill → 输出短视频

使用示例：
    agent = VideoShortsAgent(api_key="sk-xxx")
    result = agent.run("input.mp4")
"""
import os
import uuid
from datetime import datetime

from python_agent.config import get_dashscope_api_key
from python_agent.skills.transcribe_skill import TranscribeSkill
from python_agent.skills.analysis_skill import AnalysisSkill
from python_agent.skills.render_skill import RenderSkill


class VideoShortsAgent:
    """短视频加工 Agent

    协调三个 Skill 的执行顺序，管理任务隔离。

    关键设计：
    1. 每个任务有独立的 UUID 目录 → 避免多任务数据污染
    2. 技能在 __init__ 中初始化 → 避免重复加载模型
    3. run() 方法是主入口 → 接收视频路径，返回结果
    """

    def __init__(self, api_key: str = None, whisper_model: str = "base"):
        """初始化 Agent 及其三个 Skill

        Args:
            api_key: DashScope API Key，为 None 时从 .env 读取
            whisper_model: Whisper 模型大小（tiny/base/small/medium/large）
        """
        print("=" * 60)
        print("  VideoShortsAgent 初始化中...")
        print("=" * 60)

        # 获取 API Key
        if api_key is None:
            api_key = get_dashscope_api_key()

        # 初始化三个 Skill
        self.transcribe = TranscribeSkill(model_size=whisper_model)
        self.analysis = AnalysisSkill(api_key=api_key)
        self.render = RenderSkill()

        print("\n[Agent] 所有技能已加载 ✓")

    def run(self, video_path: str, output_base: str = "output") -> dict:
        """执行完整的短视频加工流程

        Args:
            video_path: 输入视频文件路径
            output_base: 输出根目录（默认 ./output）

        Returns:
            包含任务信息和结果的字典：
            {
                "task_id": "uuid",
                "input": "原始视频路径",
                "transcript_path": "转录文件路径",
                "analysis": {start, end, hook_text},
                "output_video": "输出视频路径",
                "status": "success" | "error"
            }
        """
        # 1. 创建任务隔离目录
        task_id = uuid.uuid4().hex[:8]
        task_dir = os.path.join(output_base, f"task_{task_id}")
        os.makedirs(task_dir, exist_ok=True)

        print("\n" + "=" * 60)
        print(f"  🎬 新任务: {task_id}")
        print(f"  📁 输入: {video_path}")
        print(f"  📂 工作目录: {task_dir}")
        print(f"  🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        result = {
            "task_id": task_id,
            "input": video_path,
            "status": "running"
        }

        try:
            # Step 1: 转录
            print("\n📝 [Step 1/3] 语音转文字...")
            transcript_path = self.transcribe.execute(video_path, task_dir)
            result["transcript_path"] = transcript_path

            # Step 2: 金句分析
            print("\n🔍 [Step 2/3] 金句分析...")
            analysis = self.analysis.execute(transcript_path)
            result["analysis"] = analysis

            # Step 3: 视频渲染
            print("\n🎨 [Step 3/3] 视频渲染...")
            output_video = self.render.execute(video_path, analysis, task_dir)
            result["output_video"] = output_video

            # 完成
            result["status"] = "success"
            print("\n" + "=" * 60)
            print(f"  ✅ 任务完成: {task_id}")
            print(f"  📹 输出: {output_video}")
            print("=" * 60)

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"\n❌ 任务失败: {e}")

        return result
