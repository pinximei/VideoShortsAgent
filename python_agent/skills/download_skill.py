"""
DownloadSkill - 视频下载技能

支持从 YouTube 等平台下载视频。
使用 yt-dlp (CLI) 实现，支持 URL 自动识别。
"""
import os
import subprocess
import glob
import json


class DownloadSkill:
    """视频下载技能"""

    def __init__(self):
        try:
            result = subprocess.run(
                ["C:\\Python310\\python.exe", "-m", "yt_dlp", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self._available = True
                print(f"[DownloadSkill] yt-dlp {result.stdout.strip()} 已就绪 ✓")
            else:
                self._available = False
                print(f"[DownloadSkill] ⚠️ yt-dlp 不可用")
        except Exception:
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

        output_template = os.path.join(output_dir, "source_video.%(ext)s")

        print(f"[DownloadSkill] 开始下载: {url}")

        # 清理之前下载的文件
        for f in glob.glob(os.path.join(output_dir, "source_video.*")):
            os.remove(f)

        # Firefox 优先（无 DPAPI 问题），Chrome 次之
        browsers = ["firefox", "chrome", "edge", None]
        last_error = None

        for browser in browsers:
            cmd = [
                "C:\\Python310\\python.exe", "-m", "yt_dlp",
                "--format", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "--merge-output-format", "mp4",
                "--output", output_template,
                "--remote-components", "ejs:github",
                "--no-playlist",
                "--print-json",
            ]

            if browser:
                cmd.extend(["--cookies-from-browser", browser])
                print(f"[DownloadSkill] 尝试使用 {browser} cookies...")
            else:
                print(f"[DownloadSkill] 尝试无 cookies 模式...")

            cmd.append(url)

            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    timeout=600, cwd=output_dir
                )

                if result.returncode == 0:
                    # 从 --print-json 输出解析信息
                    try:
                        # print-json 输出可能在最后一行
                        json_lines = [l for l in result.stdout.strip().split("\n") if l.startswith("{")]
                        if json_lines:
                            info = json.loads(json_lines[-1])
                            title = info.get("title", "unknown")
                            duration = info.get("duration", 0)
                        else:
                            title = "unknown"
                            duration = 0
                    except Exception:
                        title = "unknown"
                        duration = 0

                    # 查找下载的文件
                    downloaded = glob.glob(os.path.join(output_dir, "source_video.*"))
                    if downloaded:
                        filename = downloaded[0]
                        file_size = os.path.getsize(filename) / (1024 * 1024)

                        print(f"[DownloadSkill] ✅ 下载完成")
                        print(f"  标题: {title}")
                        print(f"  时长: {duration}s ({duration // 60}分{duration % 60}秒)")
                        print(f"  文件: {filename} ({file_size:.1f} MB)")
                        return filename
                    else:
                        last_error = "下载完成但未找到输出文件"
                        continue
                else:
                    stderr = result.stderr or ""
                    error_lower = stderr.lower()
                    if any(k in error_lower for k in ["cookie", "database", "permission", "dpapi", "sign in", "not a bot", "decrypt"]):
                        browser_name = browser or "无cookies"
                        print(f"[DownloadSkill] ⚠️ {browser_name} 失败: {stderr[:150]}")
                        last_error = stderr[:300]
                        continue
                    else:
                        last_error = stderr[:300]
                        continue

            except subprocess.TimeoutExpired:
                last_error = "下载超时（600秒）"
                continue
            except Exception as e:
                last_error = str(e)
                continue

        raise RuntimeError(
            f"下载失败: {last_error}\n"
            "解决方法：\n"
            "1. 安装 Firefox 并登录 YouTube\n"
            "2. 或者用 Bilibili 等其他平台链接\n"
            "3. 或者手动下载视频后上传"
        )
