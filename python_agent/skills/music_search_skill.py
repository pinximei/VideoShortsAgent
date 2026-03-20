"""
MusicSearchSkill - 在线音乐搜索技能

基于 Freesound API 搜索无版权背景音乐，支持按关键词搜索和 MP3 下载。
搜索结果缓存到本地，避免重复下载。

Freesound API 文档: https://freesound.org/docs/api/
API Key 免费获取: https://freesound.org/apiv2/apply/
"""
import os
import json
import urllib.request
import urllib.parse
from python_agent.config import get_config

# 缓存目录
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CACHE_DIR = os.path.join(_PROJECT_ROOT, "assets", "bgm", "cache")

# Freesound API 基础 URL
FREESOUND_API_BASE = "https://freesound.org/apiv2"


class MusicSearchSkill:
    """在线音乐搜索技能"""

    def __init__(self):
        self.api_key = get_config().freesound_api_key

    def is_available(self) -> bool:
        """检查 API Key 是否已配置"""
        return bool(self.api_key)

    def search(self, query: str, max_duration: int = 120,
               min_duration: int = 30, page_size: int = 5) -> list:
        """搜索背景音乐

        Args:
            query: 搜索关键词（英文效果更好），例如 "upbeat technology"
            max_duration: 最大时长（秒）
            min_duration: 最小时长（秒）
            page_size: 返回结果数量

        Returns:
            搜索结果列表，每项包含 id, name, duration, username, license, preview_url
            API Key 未配置时返回空列表
        """
        if not self.api_key:
            print("[MusicSearchSkill] ⚠️ 未配置 FREESOUND_API_KEY，跳过在线搜索")
            return []

        params = urllib.parse.urlencode({
            "token": self.api_key,
            "query": query,
            "filter": f"duration:[{min_duration} TO {max_duration}]",
            "fields": "id,name,duration,previews,tags,username,license",
            "page_size": page_size,
            "sort": "rating_desc",
        })
        url = f"{FREESOUND_API_BASE}/search/text/?{params}"

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "VideoShortsAgent/1.0"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[MusicSearchSkill] ⚠️ 搜索失败: {e}")
            return []

        results = []
        for item in data.get("results", []):
            previews = item.get("previews", {})
            # 优先使用高质量 preview
            preview_url = (
                previews.get("preview-hq-mp3")
                or previews.get("preview-lq-mp3")
                or ""
            )
            if not preview_url:
                continue

            results.append({
                "id": item.get("id"),
                "name": item.get("name", "未知"),
                "duration": round(item.get("duration", 0), 1),
                "username": item.get("username", ""),
                "license": item.get("license", ""),
                "preview_url": preview_url,
            })

        print(f"[MusicSearchSkill] 搜索 '{query}' → {len(results)} 条结果")
        return results

    def download(self, sound_id: int, preview_url: str,
                 output_dir: str = None) -> str:
        """下载音乐文件

        优先从缓存读取，未命中则下载 preview MP3。

        Args:
            sound_id: Freesound 音频 ID
            preview_url: preview MP3 的下载 URL
            output_dir: 可选的输出目录，默认使用全局缓存目录

        Returns:
            下载后的本地 MP3 文件路径
        """
        # 缓存目录
        cache_dir = output_dir or CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)

        cache_path = os.path.join(cache_dir, f"freesound_{sound_id}.mp3")

        # 缓存命中
        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1024:
            print(f"[MusicSearchSkill] 缓存命中: {cache_path}")
            return cache_path

        # 下载
        try:
            print(f"[MusicSearchSkill] 下载音乐 ID={sound_id}...")
            urllib.request.urlretrieve(preview_url, cache_path)

            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1024:
                size_kb = os.path.getsize(cache_path) / 1024
                print(f"[MusicSearchSkill] ✅ 下载完成: {cache_path} ({size_kb:.0f}KB)")
                return cache_path
            else:
                print("[MusicSearchSkill] ⚠️ 下载的文件过小，可能无效")
                return ""
        except Exception as e:
            print(f"[MusicSearchSkill] ⚠️ 下载失败: {e}")
            return ""

    def search_and_download(self, query: str, output_dir: str = None,
                            max_duration: int = 120) -> str:
        """搜索并下载评分最高的一首（便捷方法）

        Args:
            query: 搜索关键词
            output_dir: 输出目录
            max_duration: 最大时长

        Returns:
            下载后的 MP3 路径，失败返回空字符串
        """
        results = self.search(query, max_duration=max_duration)
        if not results:
            return ""
        top = results[0]
        return self.download(top["id"], top["preview_url"], output_dir)
