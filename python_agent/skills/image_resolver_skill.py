"""
ImageResolverSkill - 图片解析技能

处理三种图片来源（按优先级）：
1. 用户上传图片 → 验证文件存在，映射到 slides
2. Pexels API 搜索 → 按 image_keywords 搜索高质量无版权图片
3. 通义万相 AI 生图 → 调用 DashScope API 生成
4. 兜底 → image=None，渲染时使用纯渐变背景
"""
import os
import json
import urllib.request
import urllib.parse
from python_agent.config import get_config


class ImageResolverSkill:
    """图片解析技能"""

    def execute(self, slides: list, user_images_dir: str = None,
                enable_ai_image: bool = False, output_dir: str = None) -> list:
        """解析并填充每个 slide 的图片

        优先级：用户上传 → Pexels 搜索 → 通义万相 AI 生图 → 渐变背景

        Args:
            slides: ComposeSkill 生成的 slides 数组
            user_images_dir: 用户上传图片所在目录
            enable_ai_image: 是否启用 AI 配图（Pexels + 万相）
            output_dir: 图片输出目录

        Returns:
            更新了 image_path 字段的 slides 数组
        """
        for i, slide in enumerate(slides):
            # 模式 1: 已指定用户图片
            if slide.get("image") and user_images_dir:
                img_path = os.path.join(user_images_dir, slide["image"])
                if os.path.exists(img_path):
                    slide["image_path"] = img_path
                    print(f"  [Slide {i+1}] 用户图片: {slide['image']}")
                else:
                    print(f"  [Slide {i+1}] ⚠️ 图片不存在: {slide['image']}")
                    slide["image_path"] = None
                continue

            # 模式 2: 自动配图（需要 enable_ai_image 且有 prompt/keywords）
            has_prompt = slide.get("image_prompt") or slide.get("image_keywords")
            if enable_ai_image and has_prompt:
                img_path = None

                # 2a: 优先 Pexels 搜索（快速、高质量）
                keywords = slide.get("image_keywords", "")
                if not keywords and slide.get("image_prompt"):
                    # 用 image_prompt 的前几个词作为搜索词
                    keywords = slide["image_prompt"]
                if keywords:
                    img_path = self._search_pexels(keywords, output_dir, i)

                # 2b: Pexels 失败 → 回退通义万相 AI 生图
                if not img_path and slide.get("image_prompt"):
                    try:
                        img_path = self._generate_image(
                            slide["image_prompt"], output_dir, i
                        )
                        if img_path:
                            print(f"  [Slide {i+1}] 万相 AI 生图完成")
                    except Exception as e:
                        print(f"  [Slide {i+1}] ⚠️ AI 生图也失败: {e}")

                slide["image_path"] = img_path
                if not img_path:
                    print(f"  [Slide {i+1}] 使用渐变背景")
                continue

            # 模式 3: 无图片
            slide["image_path"] = None

        has_images = sum(1 for s in slides if s.get("image_path"))
        print(f"[ImageResolverSkill] ✅ {has_images}/{len(slides)} 个 slides 有图片")
        return slides

    def _search_pexels(self, query: str, output_dir: str, index: int) -> str:
        """从 Pexels 搜索并下载图片

        Args:
            query: 搜索关键词（英文效果最佳）
            output_dir: 图片保存目录
            index: slide 序号

        Returns:
            图片本地路径，失败返回空字符串
        """
        config = get_config()
        api_key = config.pexels_api_key
        if not api_key:
            return ""

        # 取关键词的前 5 个词
        search_query = " ".join(query.split()[:5])
        params = urllib.parse.urlencode({
            "query": search_query,
            "per_page": 1,
            "orientation": "portrait",  # 竖屏优先
        })
        url = f"https://api.pexels.com/v1/search?{params}"

        try:
            req = urllib.request.Request(url, headers={
                "Authorization": api_key,
                "User-Agent": "VideoShortsAgent/1.0"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            photos = data.get("photos", [])
            if not photos:
                print(f"  [Slide {index+1}] Pexels 未找到: '{search_query}'")
                return ""

            # 取第一张图的 large 尺寸
            photo = photos[0]
            img_url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large", "")
            if not img_url:
                return ""

            os.makedirs(output_dir, exist_ok=True)
            img_path = os.path.join(output_dir, f"pexels_{index}.jpg")
            urllib.request.urlretrieve(img_url, img_path)

            if os.path.exists(img_path) and os.path.getsize(img_path) > 1024:
                photographer = photo.get("photographer", "")
                print(f"  [Slide {index+1}] Pexels 配图: {photographer}")
                return img_path
            return ""

        except Exception as e:
            print(f"  [Slide {index+1}] Pexels 搜索失败: {e}")
            return ""

    def _generate_image(self, prompt: str, output_dir: str, index: int) -> str:
        """调用通义万相 API 生成图片"""
        config = get_config()
        api_key = config.llm_api_key

        print(f"  [Slide {index+1}] AI 生图: {prompt[:50]}...")

        try:
            from dashscope import ImageSynthesis
            result = ImageSynthesis.call(
                api_key=api_key,
                model="wanx-v1",
                prompt=prompt,
                n=1,
                size="1024*1024"
            )

            if result.status_code == 200 and result.output:
                img_url = result.output.results[0].url
                img_path = os.path.join(output_dir, f"ai_image_{index}.png")
                urllib.request.urlretrieve(img_url, img_path)
                return img_path
            else:
                raise RuntimeError(f"API 返回错误: {result.message}")

        except ImportError:
            # dashscope 未安装，尝试 HTTP API 回退
            return self._generate_image_http(prompt, output_dir, index, api_key)

    def _generate_image_http(self, prompt: str, output_dir: str,
                              index: int, api_key: str) -> str:
        """HTTP API 回退方式调用通义万相"""
        import time

        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }
        body = json.dumps({
            "model": "wanx-v1",
            "input": {"prompt": prompt},
            "parameters": {"n": 1, "size": "1024*1024"}
        }).encode()

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())

        task_id = result.get("output", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"提交生图任务失败: {result}")

        # 轮询等待
        status_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        for _ in range(60):
            time.sleep(2)
            req = urllib.request.Request(status_url, headers={"Authorization": f"Bearer {api_key}"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = json.loads(resp.read())

            task_status = status.get("output", {}).get("task_status")
            if task_status == "SUCCEEDED":
                img_url = status["output"]["results"][0]["url"]
                img_path = os.path.join(output_dir, f"ai_image_{index}.png")
                urllib.request.urlretrieve(img_url, img_path)
                return img_path
            elif task_status in ("FAILED", "UNKNOWN"):
                raise RuntimeError(f"生图任务失败: {status}")

        raise RuntimeError("生图任务超时")
