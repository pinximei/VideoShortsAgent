"""
VideoShortsAgent 桌面版：原生窗口 + 内嵌 Gradio（本地 127.0.0.1）。

启动：
    python -m python_agent.desktop
或双击 start_pc.bat
"""
from __future__ import annotations

import socket
import sys
import threading
import time

from python_agent.paths import prepend_ffmpeg_to_path, project_root


def _free_port(preferred: int) -> int:
    for port in (preferred, preferred + 1, preferred + 2, preferred + 9):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


def _run_gradio(port: int) -> None:
    import gradio as gr

    from python_agent.app import create_app

    app = create_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=port,
        share=False,
        inbrowser=False,
        show_error=True,
        theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="blue"),
        css="""
        .main-title { text-align: center; margin-bottom: 0; }
        .subtitle { text-align: center; color: #666; margin-top: 0; }
        .log-box textarea { font-family: Consolas, Monaco, monospace !important; font-size: 12px !important; }
        .edition-badge { text-align: center; margin: 0.5rem 0 1rem; color: #4338ca; }
        """,
    )


def main() -> None:
    root = project_root()
    if root not in sys.path:
        sys.path.insert(0, root)

    os.environ.setdefault("VSA_USE_USER_CONFIG", "1")
    from python_agent.config import load_env_files

    load_env_files()
    prepend_ffmpeg_to_path()

    try:
        import webview
    except ImportError:
        print("缺少 pywebview，请执行: pip install pywebview")
        print("将改用系统浏览器打开…")
        webview = None  # type: ignore

    from python_agent.config import get_config

    port = _free_port(get_config().server_port)
    url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=_run_gradio, args=(port,), daemon=True)
    thread.start()

    for _ in range(80):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                break
        except OSError:
            time.sleep(0.25)
    else:
        print(f"Gradio 未在 {url} 启动，请检查依赖与端口")
        sys.exit(1)

    title = "VideoShorts Studio"
    if webview is None:
        import webbrowser

        webbrowser.open(url)
        print(f"已在浏览器打开 {url}，按 Ctrl+C 结束")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        return

    window = webview.create_window(title, url, width=1280, height=860, min_size=(960, 640))
    webview.start(debug=False)


if __name__ == "__main__":
    main()
