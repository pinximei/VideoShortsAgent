"""
ComposeSkill - 内容编排技能 (Two-Pass Visual Director Architecture)

Pass 1: 内容脑 - 专职撰写文案、对齐时轨。
Pass 2: 视觉导演脑 - 专职挑选海量特效、运镜、生图指导。
"""
import json
import os
import re
from python_agent.llm_client import create_llm_client
from python_agent.config import get_config

class ComposeSkill:
    """Agentic LLM 视觉导演技能"""

    def __init__(self):
        config = get_config()
        self.client = create_llm_client(config.llm_api_key, config.llm_base_url)
        self.model = config.llm_model

    def execute(self, text: str, scene_type: str, visual_style: str = "auto",
                image_filenames: list = None,
                image_mode: str = "search") -> dict:
        """多轮规划编排（Agentic Visual Design）"""
        
        print(f"[ComposeSkill] 🎬 Agent 视觉导演工作流启动 (Scene: {scene_type}, Style: {visual_style})")
        print(f"  > 阶段 0: 分析文本，拆解全局分镜大纲与风格预设...")
        outline_obj = self._generate_outline(text, scene_type, visual_style)
        outline = outline_obj.get("outline", [])
        if not outline:
            raise RuntimeError("无法生成分镜大纲")
            
        global_color_mood = outline_obj.get("global_color_mood", visual_style)
        if global_color_mood == "auto" or not global_color_mood:
            global_color_mood = "tech_blue" # fallback

        total = len(outline)
        print(f"  > 剧本大纲生成成功，共 {total} 镜。当集色彩预定义: {global_color_mood}")

        slides_out = []

        print(f"  > 阶段 1 (Pass 1 - 剧情文案策划): 逐镜进行剧本文案与 Audio-Sync 打点设计...")
        for i, slide in enumerate(outline):
            print(f"    - 设计文案分镜 {i+1}/{total}...")
            designed = self._design_content_pass(slide, i, total)
            slides_out.append(designed)

        script = {"slides": slides_out}

        print(f"  > 阶段 2 (Pass 2 - 顶级视觉导演): 根据剧本流，全局下发海量特效与转场指令...")
        script = self._apply_visual_director_pass(script, global_color_mood, image_filenames, image_mode)

        global_layout_style = outline_obj.get("global_layout_style", "center")
        # 统一全剧排版风格
        for slide in script.get("slides", []):
            if "visual_design" not in slide:
                slide["visual_design"] = {}
            slide["visual_design"]["layout_style"] = global_layout_style

        script = self._validate_script(script)

        total_chars = sum(len(s.get("tts_text", "")) for s in script.get("slides", []))
        print(f"[ComposeSkill] ✅ 双脑导演编排完毕: {total} 个分镜, 总旁白 {total_chars} 字。剧情与海量张力特效全部加载。")
        return script

    def _generate_outline(self, text: str, scene_type: str, visual_style: str) -> dict:
        style_prompt = ""
        if visual_style == "auto":
            style_prompt = "\n【全局视觉预设】\n请作为视觉总监，根据文本题材自主决定一个最完美的全局色彩情绪字典（global_color_mood，用代表性英文组合如 'cyberpunk-neon'）以及全片统一的文字排版风格（global_layout_style）。并在返回 JSON 中增加 'global_color_mood' 和 'global_layout_style' 字段。"
        else:
            style_prompt = "\n【全局视觉预设】\n请作为视觉总监，结合全局基调，为全片统一决定一个文字排版风格（global_layout_style）。并在返回 JSON 中增加 'global_layout_style' 字段。"

        prompt = f"""你是一个顶级的短视频剧本编剧兼主创策划。
请根据以下输入文本，生成一个极具强感染力的结构化分镜大纲（3-6个分镜）。

输入文本：
{text}
{style_prompt}

请只返回纯 JSON，严格遵循以下格式：
{{
  "global_color_mood": "如果是auto请返回你决定的基调，如果非auto返回默认即可",
  "global_layout_style": "从 center(居中), split-left(极左对齐), split-right(极右对齐), top-heavy(顶部压迫) 中选一个最适合全片的排版模式",
  "outline": [
    {{
      "type": "title_card (开场强推) 或 content_card (中间层层推进) 或 cta_card (震撼结尾)",
      "tts_text": "本镜头的解说旁白，口语化，具有强烈的感染力（30-70字左右）"
    }}
  ]
}}
"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            timeout=90.0,
            max_tokens=800
        )
        res = getattr(response.choices[0].message, 'content', '') or ''
        reasoning = getattr(response.choices[0].message, 'reasoning_content', '') or ''
        return self._extract_json(res, reasoning)

    def _design_content_pass(self, outline_slide: dict, index: int, total: int) -> dict:
        """Pass 1: 仅负责文案、时轨对齐，卸下视觉包袱"""
        tts = outline_slide.get("tts_text", "")
        ctype = outline_slide.get("type", "content_card")
        
        prompt = f"""你是一个极致的短视频剧本编剧。
现在请为第 {index+1}/{total} 镜撰写屏幕文案与弹入触发逻辑。你只需要考虑文字内容的生猛程度！无需理会特效。

【本镜核心旁白(TTS)】: {tts}

无论前四种如何搭配，必须保证：
1. 提取极具张力的短字幕或标题显示在屏幕上！绝对不允许在画面上留白不显文字！
2. 字数越少越狠，排版才会宏大！"tts_text": "{tts}" (原封不动抄过来)
3. "heading": "凝练的大标题(极少字数冲击，10字以内)"
4. "hook_text": "左上角标签词"

【智能时轨 - Audio/Visual Sync】
针对这句旁白 "{tts}"，我们要让文字严格随声音“踩点”弹出！
5. "heading_trigger": "从上面旁白中挑选 2-4 个字，当旁白播到这几个字时，大标题弹入。"
6. "bullets": [
  {{"text": "列印的第一条副文本要点", "trigger": "选出旁白对应这点的原话词汇(必须完全匹配)"}},
  ...
] (如果没有要点可传空数组)

严格返回合法的纯 JSON 对象。
"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            timeout=120.0,
            max_tokens=800
        )
        res = getattr(response.choices[0].message, 'content', '') or ''
        reasoning = getattr(response.choices[0].message, 'reasoning_content', '') or ''
        return self._extract_json(res, reasoning)

    def _apply_visual_director_pass(self, script: dict, global_color_mood: str, image_filenames: list, image_mode: str) -> dict:
        """Pass 2: 专属于好莱坞大导演的大型视觉特效分配"""
        
        # 将剧本大纲简化为供 LLM 阅读的 JSON 文本
        simplified_slides = []
        for i, s in enumerate(script.get("slides", [])):
            simplified_slides.append({
                "index": i,
                "type": s.get("type"),
                "heading": s.get("heading"),
                "tts_text": s.get("tts_text")
            })
            
        script_text = json.dumps(simplified_slides, ensure_ascii=False, indent=2)
        img_instruction = self._build_image_instruction(image_filenames, image_mode)

        prompt = f"""你是一位荣获奥斯卡奖的先锋视觉特效导演 (Visual Director)。
现在，编剧已经把整个短视频的纯文字剧本交给了你。你的核心任务是：给每一帧注入极度强烈的“镜头语言”与“海量特效”，打破无聊单调！
你的武器库（特效表）极大，请发散思维，不要每一帧用一样的！绝对不要平庸！

【全局基调】: {global_color_mood}
【已有剧本】:
{script_text}

【你的极限特效武器库】
*为剧本的每一镜（从 0 开始），你必须分配以下完整配置：*
1. "camera_pan" (运镜): zoom-in, zoom-out, pan-left, pan-right, pan-up, pan-down, scale-rotate,能力库定义 (Capabilities)：
1. text_effect (标题动效)：glitch(赛博故障), neon(霓虹闪烁), cinematic(电影淡入), classic(微动效)。
2. caption_style (底部字幕动效)：typewriter(骇客打字机，逐字跃阶), fade(悬疑幽灵渐入), spring(动感Q弹弹入)。
3. particle_type (粒子视觉)：glow(氛围光晕，百搭), ring(科幻旋转环), matrix(数字代码雨), starfield(太空穿梭), bokeh(唯美大光斑)。
4. decoration_style (图层滤镜)：film-grain(胶片噪点), cyber-grid(赛博网格), cinematic-bars(电影宽幅黑条), none(无)。
4. transition_to_next (进场转场)：从 20 种高维空间切片中挑选 (fade, radial, circlecrop, wipeleft, wiperight, slideup, slidedown... 自由发散，极尽想象力！不要用平庸的 fade)。
注：每一镜应当根据情绪起伏选择不同的转场与粒子，不要让相邻的两镜看起来一样！的切换打破视觉疲劳！*
6. "transition_to_next" (FFmpeg 高能转场): 如果不是最后一镜，请从兼容度最高的这挑一个：radial, circlecrop, fade, dissolve, smoothleft, smoothright, wipeleft, wiperight, slideup, slidedown。（第一镜填 ""，最后一镜填 ""）（绝对禁止自创，且禁止使用 pixelize, distance, diagtl 等实验性转场避免系统崩溃！）
7. "image_prompt" & "needs_image": {img_instruction}。若开启生图，请撰写极具《视觉张力》与《电影打光》的超长生猛提示词！

【特别军令：第 0 镜的爆点原则】
起手式必须是王炸！绝不可用 static 运镜，必须选一组攻击性极强的组合（如 scale-rotate + cinematic + cinematic-bars）。

请直接返回 JSON：
{{
  "visuals": [
    {{
      "visual_design": {{
         "camera_pan": "...",
         "particle_type": "...",
         "decoration_style": "...",
         "text_effect": "...",
         "caption_style": "...",
         "color_mood": "{global_color_mood} 的变体，如 深邃宇宙蓝 等",
         "transition_to_next": "..."
      }},
      "image_prompt": "...",
      "needs_image": true或false
    }},
    ... (剧本有几镜这里就跟几条)
  ]
}}
"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            timeout=180.0,
            max_tokens=2500
        )
        res = getattr(response.choices[0].message, 'content', '') or ''
        reasoning = getattr(response.choices[0].message, 'reasoning_content', '') or ''
        visual_obj = self._extract_json(res, reasoning)
        
        # 将生成的 visual_design 缝合回原剧本
        v_list = visual_obj.get("visuals", [])
        for i, slide in enumerate(script.get("slides", [])):
            if i < len(v_list):
                v_data = v_list[i]
                slide["visual_design"] = v_data.get("visual_design", {})
                slide["caption_style"] = slide["visual_design"].get("caption_style", "spring")
                slide["image_prompt"] = v_data.get("image_prompt", "")
                slide["image_keywords"] = v_data.get("image_keywords", "")
                slide["needs_image"] = v_data.get("needs_image", False)
                slide["visual_design"]["transition_to_next"] = slide["visual_design"].get("transition_to_next", "fade")
        
        return script

    def _build_image_instruction(self, image_filenames: list, image_mode: str) -> str:
        img_instruction = "若本镜纯说理无需配图，设 `needs_image`: false"
        if image_filenames:
            img_instruction = f"用户上传了真实业务图片，请尽量从列表 {image_filenames} 中挑选最符合的一张作为 `image` 的值。如果没有合适的或没传，务必设 needs_image:true 让下游生成配图！！"

        if image_mode == "search":
            return f"""
7. "image_keywords" & "needs_image": {img_instruction}。若需要网图，请提供 `image_keywords`，仅用2-5个极简的【纯英文】核心组合词（如 "cyberpunk city", "hacked computer", "happy team"）覆盖重点，用于全球图库搜索引擎精确匹配，千万不要写长句！设 needs_image:true。"""
        elif image_mode == "ai":
            return f"""
7. "image_prompt" & "needs_image": {img_instruction}。若开启 AI 生图，请填写 `image_prompt`，撰写极具《视觉张力》与《电影打光》的超长生猛提示词！设 needs_image:true。"""
        else:
            return '\n7. "needs_image": 请固定输出 false（全局关闭插图）。'

    def _extract_json(self, content: str, reasoning: str = "") -> dict:
        for text in [content, reasoning]:
            if not text:
                continue
            text = text.strip()
            try:
                obj = json.loads(text)
                if isinstance(obj, dict): return obj
            except:
                pass

            clean = re.sub(r'```(?:json)?\s*', '', text).strip()
            try:
                obj = json.loads(clean)
                if isinstance(obj, dict): return obj
            except:
                pass

            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    obj = json.loads(match.group())
                    if isinstance(obj, dict): return obj
                except:
                    pass
        raise ValueError(f"无法从大模型提取 JSON:\n{content}")

    def _validate_script(self, script: dict) -> dict:
        if "slides" not in script:
            raise ValueError("脚本缺失 slides 字段")
        for i, slide in enumerate(script["slides"]):
            if "visual_design" not in slide:
                slide["visual_design"] = {
                    "camera_pan": "zoom-in",
                    "particle_type": "glow",
                    "decoration_style": "none",
                    "text_effect": "classic",
                    "layout_style": "center",
                    "color_mood": "dark-blue",
                    "transition_to_next": "fade" if i < len(script["slides"])-1 else ""
                }
            vd = slide["visual_design"]
            slide["transition_to_next"] = vd.get("transition_to_next", "fade")
        return script
