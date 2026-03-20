"""
PublishSkill - 发布文案与文档生成技能

使用 LLM 为视频内容自动生成：
1. 小红书发布文案（标题 + 正文 + 话题标签）
2. 功能文档（Markdown 格式）
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


class PublishSkill:
    """发布文案生成技能"""

    def __init__(self):
        config = get_config()
        self.client = create_llm_client(config.llm_api_key, config.llm_base_url)
        self.model = config.llm_model

    def execute(self, script: dict, input_text: str, scene_type: str) -> dict:
        """生成发布文案和功能文档

        Args:
            script: ComposeSkill 生成的视频脚本
            input_text: 用户原始输入文本
            scene_type: 场景类型

        Returns:
            {"xiaohongshu": {"title": "...", "content": "...", "tags": "..."},
             "doc": "## Markdown 文档..."}
        """
        prompt_template = _load_prompt("publish_copywrite.txt")

        script_str = json.dumps(script, ensure_ascii=False, indent=2)
        prompt = prompt_template.replace("{script_json}", script_str)
        prompt = prompt.replace("{input_text}", input_text)
        prompt = prompt.replace("{scene_type}", scene_type)

        print(f"[PublishSkill] 生成发布文案...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content or ""

        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # 尝试从 reasoning_content 提取
            import re
            reasoning = getattr(response.choices[0].message, 'reasoning_content', '') or ''
            for text in [result_text, reasoning]:
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    try:
                        result = json.loads(match.group())
                        break
                    except json.JSONDecodeError:
                        continue
            else:
                result = self._fallback_result(script, scene_type)

        # 确保字段完整
        if "xiaohongshu" not in result:
            result["xiaohongshu"] = self._generate_fallback_xhs(script, scene_type)
        if "doc" not in result:
            result["doc"] = self._generate_fallback_doc(script, input_text)

        print(f"[PublishSkill] ✅ 文案生成完成")
        return result

    def format_xiaohongshu(self, result: dict) -> str:
        """格式化小红书文案为可复制文本"""
        xhs = result.get("xiaohongshu", {})
        title = xhs.get("title", "")
        content = xhs.get("content", "")
        tags = xhs.get("tags", "")
        return f"📌 {title}\n\n{content}\n\n{tags}"

    def _fallback_result(self, script: dict, scene_type: str) -> dict:
        """LLM 解析失败时的回退"""
        return {
            "xiaohongshu": self._generate_fallback_xhs(script, scene_type),
            "doc": ""
        }

    def _generate_fallback_xhs(self, script: dict, scene_type: str) -> dict:
        """回退：从脚本提取基本文案"""
        slides = script.get("slides", [])
        title = slides[0].get("heading", "新视频") if slides else "新视频"
        content_parts = []
        for s in slides:
            if s.get("tts_text"):
                content_parts.append(s["tts_text"])
        return {
            "title": f"✨ {title}",
            "content": "\n".join(content_parts[:3]),
            "tags": "#短视频 #AI工具"
        }

    def _generate_fallback_doc(self, script: dict, input_text: str) -> str:
        """回退：基本文档"""
        slides = script.get("slides", [])
        title = slides[0].get("heading", "功能说明") if slides else "功能说明"
        return f"## {title}\n\n{input_text[:500]}"
