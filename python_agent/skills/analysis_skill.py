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
from openai import OpenAI


# 发送给 Qwen 的提示词模板
ANALYSIS_PROMPT = """你是一个爆款短视频内容专家。

请从以下视频转录文本中，选出一段最有"爆款潜力"的片段。

要求：
1. 片段长度在 15-30 秒之间
2. 内容要有吸引力，能在前 3 秒抓住注意力
3. 返回 JSON 格式，包含以下字段：
   - start: 开始时间（秒）
   - end: 结束时间（秒）
   - hook_text: 精简后的金句文案（用于字幕显示）

转录文本：
{transcript}

请只返回纯 JSON 对象，不要使用 markdown 代码块（```）包裹，不要添加任何其他文字说明。
返回格式示例：
{"start": 12.5, "end": 28.3, "hook_text": "你的金句文案"}"""


class AnalysisSkill:
    """金句抽取技能

    通过 LLM（Qwen-Max）分析转录文本，找出最有传播力的片段。

    Attributes:
        client: OpenAI 兼容客户端
            - base_url 指向 DashScope 的兼容端点
            - 这样就能用 openai 的 SDK 调用 Qwen 模型
    """

    def __init__(self, api_key: str, model: str = "qwen3.5-flash"):
        """初始化 Qwen 客户端

        Args:
            api_key: DashScope API Key
            model: Qwen 模型名称（qwen-max / qwen-plus / qwen-turbo）
        """
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        print(f"[AnalysisSkill] 已初始化 Qwen 客户端 (model={model}) ✓")

    def execute(self, transcript_path: str) -> dict:
        """执行金句分析

        Args:
            transcript_path: transcript.json 文件路径

        Returns:
            包含 start, end, hook_text 的字典
        """
        # 1. 读取转录文件
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = json.load(f)

        # 将 transcript 列表格式化为可读文本
        transcript_text = json.dumps(transcript, ensure_ascii=False, indent=2)
        print(f"[AnalysisSkill] 文本长度: {len(transcript_text)} 字符, {len(transcript)} 个片段")

        # 2. 构建提示词
        prompt = ANALYSIS_PROMPT.replace("{transcript}", transcript_text)

        # ========== 调试日志：LLM 输入 ==========
        print(f"\n{'='*60}")
        print(f"  📤 LLM 调用 #1: AnalysisSkill")
        print(f"  模型: {self.model}")
        print(f"  API: {self.client.base_url}")
        print(f"{'='*60}")
        print(f"  [发送的 messages]:")
        print(f"    role: user")
        print(f"    content ({len(prompt)} 字符):")
        print(f"    ---prompt 开始---")
        print(prompt[:500])  # 打印前500字符避免太长
        if len(prompt) > 500:
            print(f"    ... (省略 {len(prompt)-500} 字符) ...")
        print(f"    ---prompt 结束---")
        print(f"  [额外参数]:")
        print(f"    response_format: json_object")
        print(f"{'='*60}")

        # 3. 调用 LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        # ========== 调试日志：LLM 输出 ==========
        msg = response.choices[0].message
        result_text = msg.content or ""
        reasoning_text = getattr(msg, 'reasoning_content', None) or ""
        usage = response.usage

        print(f"\n{'='*60}")
        print(f"  📥 LLM 响应:")
        print(f"{'='*60}")
        print(f"  [Token 用量]:")
        print(f"    输入 tokens: {usage.prompt_tokens if usage else '?'}")
        print(f"    输出 tokens: {usage.completion_tokens if usage else '?'}")
        print(f"    总计 tokens: {usage.total_tokens if usage else '?'}")
        print(f"  [content ({len(result_text)}字)]:")
        print(f"    {result_text[:500]}")
        if reasoning_text:
            print(f"  [reasoning_content ({len(reasoning_text)}字)]:")
            print(f"    {reasoning_text[:300]}")
        print(f"{'='*60}\n")

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
        print(f"[_extract_json] 原始文本({len(text)}字): {repr(text[:300])}")

        # 方法 1：直接解析
        try:
            obj = json.loads(text)
            print(f"[_extract_json] 方法 1 成功: type={type(obj).__name__}")
            if isinstance(obj, dict):
                return obj
            print(f"[_extract_json] 方法 1 结果不是 dict: {repr(obj)[:200]}")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[_extract_json] 方法 1 失败: {e}")

        # 方法 2：去掉 markdown 代码块
        clean = re.sub(r'```(?:json)?\s*', '', text)
        clean = clean.strip()
        try:
            obj = json.loads(clean)
            print(f"[_extract_json] 方法 2 成功: type={type(obj).__name__}")
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[_extract_json] 方法 2 失败: {e}")

        # 方法 3：正则提取第一个 {...}
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
        if match:
            print(f"[_extract_json] 方法 3 匹配到: {repr(match.group()[:200])}")
            try:
                obj = json.loads(match.group())
                if isinstance(obj, dict):
                    return obj
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[_extract_json] 方法 3 失败: {e}")

        raise ValueError(f"无法从 LLM 输出中提取 JSON 对象: {text[:300]}")
