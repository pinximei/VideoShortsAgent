"""
analyze Skill 执行器

标准 Skill 执行器接口：
    execute(args: dict, context: dict) -> str

Args:
    args: 从 LLM 回复中解析出的参数字典
    context: Agent 运行时上下文（api_key, model, task_dir 等）

Returns:
    执行结果的字符串（会回传给 LLM）
"""
import json
from python_agent.skills.analysis_skill import AnalysisSkill


# 缓存 AnalysisSkill 实例，避免重复创建
_cached_skill = None


def execute(args: dict, context: dict) -> str:
    """执行金句分析

    Args:
        args: {"transcript_path": "path/to/transcript.json"}
        context: {"api_key": "...", "model": "...", "task_dir": "..."}

    Returns:
        分析结果的 JSON 字符串
    """
    global _cached_skill

    transcript_path = args.get("transcript_path")
    if not transcript_path:
        return "错误：缺少必需参数 transcript_path"

    # 延迟初始化
    if _cached_skill is None:
        api_key = context.get("api_key", "")
        model = context.get("model", "qwen3.5-flash")
        _cached_skill = AnalysisSkill(api_key=api_key, model=model)

    try:
        result = _cached_skill.execute(transcript_path)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"执行失败：{e}"
