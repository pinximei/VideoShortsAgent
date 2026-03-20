"""
ComposeSkill - 内容编排技能

使用 LLM 将纯文本（招聘 JD、公司简介等）编排为结构化的视频脚本。
根据 templates/scenes/ 中的场景模板加载 prompt 和配置。
"""
import json
import os
from python_agent.llm_client import create_llm_client
from python_agent.config import get_config
from python_agent.template_loader import load_scenes


class ComposeSkill:
    """LLM 内容编排技能"""

    def __init__(self):
        config = get_config()
        self.client = create_llm_client(config.llm_api_key, config.llm_base_url)
        self.model = config.llm_model
        self.scenes = load_scenes()

    def execute(self, text: str, scene_type: str,
                image_filenames: list = None,
                enable_ai_image: bool = False) -> dict:
        """将文本编排为视频脚本

        Args:
            text: 用户输入的原始文本
            scene_type: 场景类型 (recruitment/company_intro/product/project_release/knowledge/general)
            image_filenames: 用户上传的图片文件名列表
            enable_ai_image: 是否启用 AI 生图

        Returns:
            视频脚本 dict，包含 slides 数组
        """
        # 1. 获取场景配置
        scene_config = self.scenes.get(scene_type)
        if not scene_config:
            scene_config = self.scenes.get("general", {})
            print(f"[ComposeSkill] 未知场景 '{scene_type}'，使用通用模板")

        # 2. 从场景模板中获取内联 prompt
        prompt_template = scene_config.get("prompt", "")
        if not prompt_template:
            raise ValueError(f"场景模板 '{scene_type}' 缺少 prompt 字段")

        # 3. 构建图片指令
        image_instruction = self._build_image_instruction(
            image_filenames, enable_ai_image
        )

        # 4. 填充 Prompt
        prompt = prompt_template.replace("{input_text}", text)
        prompt = prompt.replace("{image_instruction}", image_instruction)

        # 5. 调用 LLM
        print(f"[ComposeSkill] 场景={scene_config['name']}, 调用 LLM ({self.model})...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content or ""
        reasoning_text = getattr(response.choices[0].message, 'reasoning_content', None) or ""

        # 6. 提取 JSON
        script = self._extract_json(result_text, reasoning_text)

        # 7. 验证和规范化
        script = self._validate_script(script)

        slides_count = len(script.get("slides", []))
        total_chars = sum(len(s.get("tts_text", "")) for s in script.get("slides", []))
        print(f"[ComposeSkill] ✅ 生成 {slides_count} 个 slides, 总字数 {total_chars}")

        return script

    def _build_image_instruction(self, image_filenames: list, enable_ai_image: bool) -> str:
        """根据图片模式构建指令"""
        if image_filenames:
            names = ", ".join(image_filenames)
            return (
                f"可用图片文件: [{names}]\n"
                "请根据每个 slide 的内容，为合适的 slide 分配 image 字段（填入文件名）。\n"
                "不是每个 slide 都需要图片，只在图片与内容匹配时才分配。\n"
                "没有分配图片的 slide 设置 needs_image: false。"
            )
        elif enable_ai_image:
            return (
                "用户没有提供图片，但希望 AI 自动配图。\n"
                "请为适合配图的 slide 添加以下字段：\n"
                "  - image_prompt: 中文描述画面场景，如 '一群年轻程序员在现代化办公室讨论'\n"
                "  - image_keywords: 2-3 个英文关键词，用空格分隔，如 'office teamwork technology'\n"
                "  - needs_image: true\n"
                "不需要配图的 slide（如标题卡、CTA）设置 needs_image: false。"
            )
        else:
            return "不使用图片，每个 slide 设置 needs_image: false。视频将使用纯色/渐变背景 + 文字动画。"

    def _extract_json(self, content: str, reasoning: str = "") -> dict:
        """从 LLM 输出中提取 JSON"""
        import re

        for text in [content, reasoning]:
            if not text:
                continue
            text = text.strip()

            # 方法 1: 直接解析
            try:
                obj = json.loads(text)
                if isinstance(obj, dict):
                    return obj
            except (json.JSONDecodeError, ValueError):
                pass

            # 方法 2: 去 markdown 代码块
            clean = re.sub(r'```(?:json)?\s*', '', text).strip()
            try:
                obj = json.loads(clean)
                if isinstance(obj, dict):
                    return obj
            except (json.JSONDecodeError, ValueError):
                pass

            # 方法 3: 正则提取
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    obj = json.loads(match.group())
                    if isinstance(obj, dict):
                        return obj
                except (json.JSONDecodeError, ValueError):
                    pass

        raise ValueError(f"无法从 LLM 输出中提取 JSON: {content[:300]}")

    def _validate_script(self, script: dict) -> dict:
        """验证和规范化脚本"""
        if "slides" not in script:
            raise ValueError("脚本缺少 slides 字段")

        valid_types = {"title_card", "content_card", "cta_card"}
        valid_styles = {"spring", "fade", "typewriter"}
        valid_transitions = {"fade", "circleopen", "wipeleft", "wiperight", "slideup", "slidedown"}

        for i, slide in enumerate(script["slides"]):
            # 类型检查
            if slide.get("type") not in valid_types:
                slide["type"] = "content_card"

            # tts_text 必须存在
            if not slide.get("tts_text"):
                slide["tts_text"] = slide.get("heading", f"第{i+1}段内容")

            # hook_text 回退
            if not slide.get("hook_text"):
                slide["hook_text"] = slide.get("heading", "")[:20]

            # caption_style 规范化
            if slide.get("caption_style") not in valid_styles:
                slide["caption_style"] = "spring"

            # transition 规范化（最后一个不需要）
            if i < len(script["slides"]) - 1:
                if slide.get("transition_to_next") not in valid_transitions:
                    slide["transition_to_next"] = "fade"
            else:
                slide.pop("transition_to_next", None)

            # needs_image 默认
            if "needs_image" not in slide:
                slide["needs_image"] = bool(slide.get("image") or slide.get("image_prompt"))

        return script
