"""
DownloadSkill - 视频下载技能

支持从 YouTube 等平台下载视频。
使用 yt-dlp 库实现，支持 URL 自动识别。
"""
import os


class DownloadSkill:
    """视频下载技能"""

    def __init__(self):
        try:
            import yt_dlp
            self._available = True
            print(f"[DownloadSkill] yt-dlp 已就绪 ✓")
        except ImportError:
            self._available = False
            print(f"[DownloadSkill] ⚠️ yt-dlp 未安装（pip install yt-dlp）")

    def execute(self, url: str, output_dir: str) -> str:
        """下载视频

        Args:
            url: 视频 URL（YouTube、Bilibili 等）
            output_dir: 输出目录

        Returns:
            下载后的视频文件路径
        """
        os.makedirs(output_dir, exist_ok=True)

        if not self._available:
            raise RuntimeError("yt-dlp 未安装，请运行: pip install yt-dlp")

        import yt_dlp

        output_template = os.path.join(output_dir, "source_video.%(ext)s")

        base_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "quiet": False,
            "no_warnings": False,
            "progress_hooks": [self._progress_hook],
        }

        print(f"[DownloadSkill] 开始下载: {url}")

        # 依次尝试不同浏览器 cookies，解决浏览器运行时数据库锁定问题
        browsers = [("edge",), ("chrome",), ("firefox",), None]
        last_error = None

        for browser in browsers:
            opts = base_opts.copy()
            if browser:
                opts["cookiesfrombrowser"] = browser
                print(f"[DownloadSkill] 尝试使用 {browser[0]} cookies...")
            else:
                print(f"[DownloadSkill] 尝试无 cookies 模式...")

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "unknown")
                    duration = info.get("duration", 0)

                    filename = ydl.prepare_filename(info)
                    if not os.path.exists(filename):
                        filename = os.path.splitext(filename)[0] + ".mp4"

                    file_size = os.path.getsize(filename) / (1024 * 1024)

                    print(f"[DownloadSkill] ✅ 下载完成")
                    print(f"  标题: {title}")
                    print(f"  时长: {duration}s ({duration // 60}分{duration % 60}秒)")
                    print(f"  文件: {filename} ({file_size:.1f} MB)")

                    return filename
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                if "cookie" in error_msg or "database" in error_msg or "permission" in error_msg:
                    browser_name = browser[0] if browser else '无cookies'
                    print(f"[DownloadSkill] ⚠️ {browser_name} 失败: {str(e)[:100]}")
                    continue
                elif "sign in" in error_msg or "not a bot" in error_msg:
                    print(f"[DownloadSkill] ⚠️ YouTube 要求登录验证，尝试下一种方式...")
                    continue
                else:
                    raise

        # 所有方式失败，给出具体指引
        raise RuntimeError(
            "YouTube 下载失败。解决方法：\n"
            "1. 关闭 Chrome 浏览器后重试（Chrome 运行时 cookies 被锁定）\n"
            "2. 或者用 Bilibili 等其他平台链接\n"
            "3. 或者手动下载视频后上传"
        )

    @staticmethod
    def _progress_hook(d):
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "?%")
            speed = d.get("_speed_str", "?")
            print(f"\r[DownloadSkill] 下载中... {percent} ({speed})", end="", flush=True)
        elif d["status"] == "finished":
            print(f"\n[DownloadSkill] 下载完成，正在处理...")
