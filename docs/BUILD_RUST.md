# Rust 版构建说明（小体积 EXE）

## 为什么改用 Rust 做 v1 壳

| | Python + PyInstaller | Rust + egui |
|--|----------------------|-------------|
| 安装包 | 常 300MB～1GB+ | **约 5～15MB**（release + strip） |
| 依赖 | 整包 Python + Gradio | 系统 WebView 不需要（egui 自绘） |
| 第一版功能 | 全功能 | **先：裁剪 / 抖音竖屏**；AI 后续接 |

## 工程结构

```
rust/
  vsa-core/    # 库：解析时间段、调 FFmpeg
  vsa-cli/     # 命令行（测试用）
  vsa-gui/     # VideoShortsStudio.exe（egui 界面）
```

## 环境

1. 安装 [rustup](https://rustup.rs)（Windows 选 MSVC 工具链）
2. 安装 **FFmpeg** 并加入 PATH（或设置 `VSA_FFMPEG` / `VSA_FFPROBE`）
3. 构建：

```bat
scripts\build_rust_release.bat
```

产物：`rust\target\release\VideoShortsStudio.exe`

## 分发清单

- `VideoShortsStudio.exe`
- `ffmpeg.exe` + `ffprobe.exe`（可放同目录 `bin\`，安装脚本写入 PATH）
- `使用说明.txt`（通义 Key 教程 — AI 版后续）
- 激活码工具（仍可用 Python 版 `tools/generate_license.py` 生成）

## 与 Python 版关系

- **Python 版**：功能全，包大，适合开发调试（`start_pc.bat`）
- **Rust 版**：先卖「剪片三件套」，包小；AI / 短剧 / 海报 **逐步迁回**（Rust 调 HTTP + 用户 Key，或子进程调 whisper）

## C++ 备选

若团队更熟 C++：可用 **Qt / wxWidgets** 做 UI，剪辑仍建议 **调 FFmpeg CLI**（与 Rust 相同思路）。Rust 优势是内存安全 + 现代包管理，体积与 C++ 同级。
