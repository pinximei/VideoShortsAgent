"""
DownloadSkill - 视频下载技能

支持从 YouTube 等平台下载视频。
使用 yt-dlp 库实现，支持 URL 自动识别。
"""
import os
import yt_dlp


class DownloadSkill:
    """视频下载技能"""

    def __init__(self):
        print(f"[DownloadSkill] yt-dlp 已就绪 ✓")

    def execute(self, url: str, output_dir: str) -> str:
        """下载视频

        Args:
            url: 视频 URL（YouTube、Bilibili 等）
            output_dir: 输出目录

        Returns:
            下载后的视频文件路径
        """
        os.makedirs(output_dir, exist_ok=True)

        output_template = os.path.join(output_dir, "source_video.%(ext)s")

        ydl_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "quiet": False,
            "no_warnings": False,
            "progress_hooks": [self._progress_hook],
        }

        print(f"[DownloadSkill] 开始下载: {url}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "unknown")
            duration = info.get("duration", 0)

            # 找到实际下载的文件
            filename = ydl.prepare_filename(info)
            # yt-dlp 可能会修改扩展名
            if not os.path.exists(filename):
                filename = os.path.splitext(filename)[0] + ".mp4"

            file_size = os.path.getsize(filename) / (1024 * 1024)  # MB

            print(f"[DownloadSkill] ✅ 下载完成")
            print(f"  标题: {title}")
            print(f"  时长: {duration}s ({duration // 60}分{duration % 60}秒)")
            print(f"  文件: {filename} ({file_size:.1f} MB)")

            return filename

    @staticmethod
    def _progress_hook(d):
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "?%")
            speed = d.get("_speed_str", "?")
            print(f"\r[DownloadSkill] 下载中... {percent} ({speed})", end="", flush=True)
        elif d["status"] == "finished":
            print(f"\n[DownloadSkill] 下载完成，正在处理...")
