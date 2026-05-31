# VideoShorts Studio（Tauri 2 + Vue 3）

桌面端 UI：深色侧栏布局，本地裁剪 / 抖音包 / 电商切片；AI 与字幕页为 BYOK 占位。

## 设计文档

见仓库根目录 [`docs/UI_DESIGN.md`](../../docs/UI_DESIGN.md)。

## UI 评审引擎

完成界面改动后，运行至少 10 轮自动评审：

```powershell
cd D:\VideoShortsAgent
py -3.12 apps\studio\tools\ui_review_engine.py --rounds 12
```

未通过时会列出具体修改建议；迭代直至终端显示 `APPROVED`。

## 环境

- [Node.js](https://nodejs.org/) 20+
- [Rust](https://rustup.rs/) stable（`cargo` 在 PATH）
- [FFmpeg](https://ffmpeg.org/)（含 `ffprobe`，PATH 或设置页指定）

## 开发

```powershell
cd D:\VideoShortsAgent\apps\studio
npm install
npm run tauri:dev
```

仅预览网页（无 FFmpeg / 无文件对话框）：

```powershell
npm run dev
```

## 打包

```powershell
npm run tauri:build
```

安装包输出在 `src-tauri/target/release/bundle/`。

首次打包前请生成图标（任选 1024×1024 PNG）：

```powershell
npm run tauri icon path\to\logo.png
```

## 目录

| 路径 | 说明 |
|------|------|
| `src/layouts/AppShell.vue` | 侧栏 + 顶栏 + 主内容 |
| `src/views/*.vue` | 各业务页 |
| `src/components/ExportWorkbench.vue` | 裁剪工作台（左右分栏） |
| `src-tauri/` | Rust 命令，调用 `rust/vsa-core` |

## Rust 命令

- `export_clip` — 解析时间段 → FFmpeg 裁剪拼接 → 可选 9:16
- `probe_video_cmd` — ffprobe 时长与分辨率
- `license_status` — 授权状态（待接 `licensing.py` 同等逻辑）
- `open_output_folder` — 打开输出目录

输出默认：`%APPDATA%\VideoShortsAgent\output\`。
