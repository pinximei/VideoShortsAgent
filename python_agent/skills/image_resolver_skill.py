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
                image_mode: str = "search", output_dir: str = None) -> list:
        """解析并填充每个 slide 的图片

        优先级：用户上传 → Pexels 搜索 → 通义万相 AI 生图 → 渐变背景

        Args:
            slides: ComposeSkill 生成的 slides 数组
            user_images_dir: 用户上传图片所在目录
            image_mode: 配图策略 (search / ai / none)
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

            # 模式 2: 自动配图（需要有 prompt/keywords 并且模式不是 none）
            has_prompt = slide.get("image_prompt") or slide.get("image_keywords")
            if image_mode != "none" and has_prompt:
                img_path = None

                if image_mode == "search":
                    keywords = slide.get("image_keywords", "")
                    if not keywords and slide.get("image_prompt"):
                        keywords = slide["image_prompt"]
                        
                    if keywords:
                        img_path = self._search_pixabay(keywords, output_dir, i)
                        if not img_path:
                            # 降级 DDG
                            img_path = self._search_duckduckgo(keywords, output_dir, i)
                            if not img_path:
                                print(f"  [Slide {i+1}] ⚠️ 网图全部失败，强制启动通义万相 AI 兜底生图...")
                                try:
                                    img_path = self._generate_image(keywords, output_dir, i)
                                    if img_path:
                                        print(f"  [Slide {i+1}] 🎨 AI 兜底生图完成!")
                                except Exception as e:
                                    print(f"  [Slide {i+1}] ⚠️ AI 兜底生图失败: {e}")
                elif image_mode == "ai":
                    if slide.get("image_prompt"):
                        try:
                            img_path = self._generate_image(
                                slide["image_prompt"], output_dir, i
                            )
                            if img_path:
                                print(f"  [Slide {i+1}] 🎨 万相 AI 生图完成!")
                        except Exception as e:
                            print(f"  [Slide {i+1}] ⚠️ AI 生图失败: {e}")

                slide["image_path"] = img_path
                if not img_path:
                    print(f"  [Slide {i+1}] 无配图，使用动态渐变特效兜底")
                continue

            # 模式 3: 无图片
            slide["image_path"] = None

        has_images = sum(1 for s in slides if s.get("image_path"))
        print(f"[ImageResolverSkill] ✅ {has_images}/{len(slides)} 个 slides 有图片")
        return slides

    def _stealth_download(self, url: str, path: str):
        """带标准浏览器 User-Agent 的下载，防止被防盗链(Cloudflare)拦截"""
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(path, "wb") as f:
                f.write(resp.read())

    def _search_pixabay(self, query: str, output_dir: str, index: int) -> str:
        """从 Pixabay 搜索影片/图片（优先使用 MP4 视频）"""
        config = get_config()
        api_key = getattr(config, 'pixabay_api_key', os.environ.get("PIXABAY_API_KEY"))
        if not api_key:
            return ""

        search_query = urllib.parse.quote(" ".join(query.split()[:5]))
        
        try:
            # 1. 尝试搜索高质量视频
            video_url = f"https://pixabay.com/api/videos/?key={api_key}&q={search_query}&orientation=horizontal&per_page=3&safesearch=true"
            req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                v_data = json.loads(resp.read().decode("utf-8"))
            
            v_hits = v_data.get("hits", [])
            if v_hits:
                # 成功找到视频
                videos = v_hits[0].get("videos", {})
                # 倾向于获取 1080p, 退而求其次 720p/medium
                best_vid = videos.get("large") or videos.get("medium") or videos.get("small")
                if best_vid and best_vid.get("url"):
                    vid_url = best_vid["url"]
                    os.makedirs(output_dir, exist_ok=True)
                    vid_path = os.path.join(output_dir, f"pixabay_{index}.mp4")
                    self._stealth_download(vid_url, vid_path)
                    if os.path.exists(vid_path) and os.path.getsize(vid_path) > 1024:
                        print(f"  [Slide {index+1}] 🎥 Pixabay 获取正版视频成功! 正在转换密集关键帧以根除重影...")
                        try:
                            import subprocess
                            tmp_path = vid_path + ".tmp.mp4"
                            os.rename(vid_path, tmp_path)
                            subprocess.run([
                                "ffmpeg", "-y", "-i", tmp_path, "-c:v", "libx264", "-g", "1",
                                "-preset", "ultrafast", "-crf", "23", "-an", vid_path
                            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                            os.remove(tmp_path)
                        except Exception as e:
                            print(f"  [Slide {index+1}] ⚠️ 转码密集关键帧失败，回退原视频: {str(e)}")
                            if os.path.exists(tmp_path) and not os.path.exists(vid_path):
                                os.rename(tmp_path, vid_path)
                        return vid_path
            
            # 2. 如果视频没找到，回退到高清图片搜索
            photo_url = f"https://pixabay.com/api/?key={api_key}&q={search_query}&image_type=photo&orientation=horizontal&per_page=3&safesearch=true"
            req = urllib.request.Request(photo_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            
            hits = data.get("hits", [])
            if not hits:
                print(f"  [Slide {index+1}] ⚠️ Pixabay (音视频/图库) 均未搜到: '{query}'")
                return ""
            
            hit = hits[0]
            img_url = hit.get("largeImageURL") or hit.get("webformatURL")
            if not img_url:
                return ""
            
            os.makedirs(output_dir, exist_ok=True)
            img_path = os.path.join(output_dir, f"pixabay_{index}.jpg")
            self._stealth_download(img_url, img_path)
            
            if os.path.exists(img_path) and os.path.getsize(img_path) > 1024:
                print(f"  [Slide {index+1}] 📸 Pixabay 顶级正版图库配图成功!")
                return img_path
            return ""
        except Exception as e:
            print(f"  [Slide {index+1}] ⚠️ Pixabay 搜索异常或不可达: {e}")
            return ""

    def _search_duckduckgo(self, query: str, output_dir: str, index: int) -> str:
        """DuckDuckGo 免费全局网图搜索"""
        try:
            from duckduckgo_search import DDGS
            search_query = " ".join(query.split()[:5])
            print(f"  [Slide {index+1}] 🔍 DDG全网搜索: {search_query} ... ", end="", flush=True)
            
            with DDGS() as ddgs:
                results = list(ddgs.images(search_query, max_results=3))
            
            if not results:
                print("空返回值")
                return ""
            
            for res in results:
                img_url = res.get("image")
                if not img_url:
                    continue
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    img_path = os.path.join(output_dir, f"ddg_{index}.jpg")
                    self._stealth_download(img_url, img_path)
                            
                    if os.path.getsize(img_path) > 1024:
                        print(f"✅ 获取成功!")
                        return img_path
                except Exception:
                    continue
            print("下载失败")
            return ""
        except ImportError:
            print("⚠️ 未安装 duckduckgo_search 库")
            return ""
        except Exception as e:
            print(f" ⚠️ DDG网络阻断或超时")
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
                self._stealth_download(img_url, img_path)
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
        print(f"  [Slide {index+1}] 开启轮询任务 {task_id[:8]}... ", end="", flush=True)
        for i in range(240): # up to 480 seconds (8 minutes)
            time.sleep(2)
            try:
                req = urllib.request.Request(status_url, headers={"Authorization": f"Bearer {api_key}"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    status = json.loads(resp.read())

                task_status = status.get("output", {}).get("task_status")
                if task_status == "SUCCEEDED":
                    print("✅ 完成!")
                    img_url = status["output"]["results"][0]["url"]
                    img_path = os.path.join(output_dir, f"ai_image_{index}.png")
                    self._stealth_download(img_url, img_path)
                    return img_path
                elif task_status in ("FAILED", "UNKNOWN"):
                    print(f"❌ 失败: {status}")
                    raise RuntimeError(f"生图任务失败: {status}")
                elif i % 15 == 0:
                    print(f"[{task_status}]", end="", flush=True)
                elif i % 3 == 0:
                    print(".", end="", flush=True)
            except Exception as e:
                if i % 10 == 0: print("?", end="", flush=True)

        print(" ⏳ 超时8分钟生图未完成, 强制切断!")
        raise RuntimeError("生图任务极度拥堵起时")
