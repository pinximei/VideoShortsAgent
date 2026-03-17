"""
AnalysisSkill - 金句抽取技能

使用阿里云 DashScope（Qwen-Max）分析转录文本，从中找出最有"爆款潜力"的
15-30 秒片段，返回结构化的剪辑方案。

核心概念：
- OpenAI 兼容 API：DashScope 提供了与 OpenAI SDK 兼容的接口，
  所以我们直接用 openai 库，只需改 base_url 即可
- response_format: 让模型强制返回 JSON 格式
- 金句：视频中最能引起观众兴趣的一段话

使用示例：
    skill = AnalysisSkill(api_key="sk-xxx")
    result = skill.execute("./output/transcript.json")
    # result -> {"start": 12.5, "end": 28.3, "hook_text": "..."}
"""
import json
import os
from python_agent.llm_client import create_llm_client
from python_agent.config import get_config

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def _load_prompt(filename: str) -> str:
    """加载提示词文件"""
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# 发送给 Qwen 的提示词模板
ANALYSIS_PROMPT = """你是一个专业的短视频内容策划专家。

请仔细阅读以下视频转录文本，理解视频讲述的完整内容，然后将其浓缩为一个连贯的短视频解说。

**核心思路**：先理解整个视频讲了什么，然后用你的语言重新组织成一段流畅的叙述，再从视频中找到与每段叙述最匹配的画面片段。

**硬性约束**：所有片段的 tts_text 字数总和不得超过 210 字（即总配音时长 ≤ 60 秒）。超出则必须删减片段或精简文案。

要求：
1. 先通读全文，理解视频的主题和核心观点
2. **转录纠错**：语音识别可能存在专有名词错误（如把 "Skills" 识别成 "Scale"），请根据上下文语义自动判断并修正这类错误，确保 tts_text 和 hook_text 中使用正确的术语
3. 将内容浓缩为 **2~4 个关键段落**（不得少于 2 个，不得超过 4 个），每段对应一个完整的核心观点
4. **内容完整性优先**：每个片段必须围绕一个主题把事情讲清楚、讲完整。宁可减少片段数量，也不要为了凑数而让某段解说含糊不清或话说一半
5. **第一个片段必须是简短的背景介绍**：交代视频的主题和背景
6. 后续片段依次讲解核心内容，每段围绕一个完整的观点展开
7. 为每段找到转录文本中最匹配的时间区间（start, end），作为视频画面来源
8. **片段时长由 tts_text 字数反推**：先写好 tts_text，然后用 tts_text 字数 ÷ 3.5 算出所需秒数，再根据这个秒数在转录文本中找到对应长度的时间区间（start, end）
9. 片段按叙述逻辑排列（通常与时间顺序一致）
10. 每个片段配一个中文字幕（hook_text），概括该段内容
11. 每个片段提供 tts_text 字段：用自然流畅的中文重新组织该段内容的解说词，用于语音合成配音
12. **字数控制**：中文语音合成速度约为每秒 4 个汉字。tts_text 的字数应控制在 (片段秒数 × 3.5) 左右，确保配音时长略短于视频画面时长，给画面留出呼吸感
13. hook_text 应与 tts_text 内容一致（可以是 tts_text 本身或其精简版）
14. 最终拼接后应完整概述视频的主题，让观众快速了解整个视频在讲什么
15. 最终输出是一个紧凑的短视频，总时长由上方硬性约束保证
16. **每段独立特效**：根据每段内容的情绪和节奏，为每个片段独立选择字幕风格和转场效果：
    - caption_style: 字幕动画风格，可选 spring (弹出，适合科技/活力) / fade (淡入，适合情感/严肃) / typewriter (打字机，适合叙事/悬疑)
    - transition_to_next: 到下一段的转场，可选 fade / circleopen / wipeleft / wiperight / slideup / slidedown（最后一段不需要）
    - 不同片段应根据内容情绪选择不同特效，避免全部用相同特效

转录文本：
{transcript}

请只返回纯 JSON 对象，不要使用 markdown 代码块（```）包裹，不要添加任何其他文字说明。
返回格式：
{"clips": [{"start": 12.5, "end": 22.3, "hook_text": "中文字幕", "tts_text": "中文解说词", "caption_style": "spring", "transition_to_next": "circleopen"}, ...]}"""

# 英文源语言时的额外指令
ANALYSIS_PROMPT_EN_ADDON = """

注意：这段视频的原始语言是英文。
额外要求：
- tts_text 不是逐字翻译，而是用自然流畅的中文重新讲述核心内容
"""


class AnalysisSkill:
    """金句抽取技能

    通过 LLM（Qwen-Max）分析转录文本，找出最有传播力的片段。

    Attributes:
        client: OpenAI 兼容客户端
            - base_url 指向 DashScope 的兼容端点
            - 这样就能用 openai 的 SDK 调用 Qwen 模型
    """

    def __init__(self, api_key: str = None, model: str = None):
        """初始化分析客户端

        Args:
            api_key: API Key（可选，默认从 Config 读取）
            model: 模型名称（可选，默认从 Config 读取 llm_analysis_model）
        """
        cfg = get_config()
        self.model = model or cfg.llm_analysis_model
        self.client = create_llm_client(api_key=api_key)
        print(f"[AnalysisSkill] 已初始化 Qwen 客户端 (model={model}) ✓")

    def execute(self, transcript_path: str) -> dict:
        """执行金句分析

        Args:
            transcript_path: transcript.json 文件路径

        Returns:
            包含 start, end, hook_text (及可能的 tts_text) 的字典
        """
        # 1. 读取转录文件（兼容新旧格式）
        with open(transcript_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # 新格式: {"language": "en", "segments": [...]}
        # 旧格式: [{"start": ..., "end": ..., "text": ...}, ...]
        if isinstance(raw_data, dict) and "segments" in raw_data:
            segments = raw_data["segments"]
            source_lang = raw_data.get("language", "zh")
        else:
            segments = raw_data
            source_lang = "zh"

        # 将 segments 格式化为可读文本
        transcript_text = json.dumps(segments, ensure_ascii=False, indent=2)
        print(f"[AnalysisSkill] 文本长度: {len(transcript_text)} 字符, {len(segments)} 个片段")
        print(f"[AnalysisSkill] 源语言: {source_lang}")

        # 2. 构建提示词（英文源时追加翻译要求）
        prompt = _load_prompt("analysis.txt").replace("{transcript}", transcript_text)
        if source_lang != "zh":
            prompt += _load_prompt("analysis_en_addon.txt")
            print(f"[AnalysisSkill] 非中文源，已追加 tts_text 翻译要求")

        # 3. 调用 LLM
        print(f"[AnalysisSkill] 调用 LLM ({self.model})...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        msg = response.choices[0].message
        result_text = msg.content or ""
        reasoning_text = getattr(msg, 'reasoning_content', None) or ""

        # 4. 从 LLM 返回中提取 JSON 对象
        #    优先从 content 提取；如果 content 为空（思考模式），从 reasoning_content 提取
        if result_text.strip():
            result = self._extract_json(result_text)
        elif reasoning_text.strip():
            print(f"[AnalysisSkill] content 为空，尝试从 reasoning_content 提取 JSON")
            result = self._extract_json(reasoning_text)
        else:
            raise ValueError("LLM 返回的 content 和 reasoning_content 都为空")

        print(f"[AnalysisSkill] 分析完成 ✓")
        clips = result.get("clips", [])
        if clips:
            print(f"  共提取 {len(clips)} 个片段:")
            for i, clip in enumerate(clips):
                print(f"  [{i+1}] {clip.get('start', '?')}s - {clip.get('end', '?')}s | {clip.get('hook_text', '?')}")
        else:
            # 兼容旧格式（单片段）
            print(f"  金句时段: {result.get('start', '?')}s - {result.get('end', '?')}s")
            print(f"  金句文案: {result.get('hook_text', '?')}")

        return result

    @staticmethod
    def _extract_json(text: str) -> dict:
        """从 LLM 输出中提取 JSON 对象

        兼容多种格式：
        - 纯 JSON
        - ```json ... ``` 包裹
        - 思考模式前后有其他文本
        """
        import re

        text = text.strip()

        # 方法 1：直接解析
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass

        # 方法 2：去掉 markdown 代码块
        clean = re.sub(r'```(?:json)?\s*', '', text)
        clean = clean.strip()
        try:
            obj = json.loads(clean)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass

        # 方法 3：正则提取第一个 {...}
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
        if match:
            try:
                obj = json.loads(match.group())
                if isinstance(obj, dict):
                    return obj
            except (json.JSONDecodeError, ValueError):
                pass

        raise ValueError(f"无法从 LLM 输出中提取 JSON 对象: {text[:300]}")
