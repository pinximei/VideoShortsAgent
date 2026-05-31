# vsa-core（Rust）— 规划中的本地视频引擎

> 阶段 1 目标：用 Rust 实现 **无 API** 的剪辑能力，供 EXE / Python UI 通过 CLI 调用。

## 计划中的二进制

```bash
vsa-cli probe   input.mp4          # 时长、分辨率、音轨
vsa-cli clip    input.mp4 out.mp4 --start 1.5 --end 10.0
vsa-cli concat  manifest.json out.mp4   # 多段拼接 + 可选 xfade
vsa-cli vertical input.mp4 out.mp4      # 9:16 裁切
```

## 计划依赖（crate）

- `ffmpeg-next` 或调用系统 `ffmpeg` 子进程（与现 Python 版一致，先子进程最快）
- `serde` / `serde_json` — 任务清单
- `clap` — CLI
- `anyhow` — 错误

## 与 Python 共存

```text
VideoShortsStudio.exe
  └─ UI (Tauri / pywebview)
       └─ 调用 vsa-cli（Rust）做裁剪
       └─ 可选 Python 子进程做 AI（BYOK）
```

## 状态

Cargo workspace 已初始化：`vsa-core` / `vsa-cli` / `vsa-gui`。

构建见仓库根目录 `scripts/build_rust_release.bat` 与 `docs/BUILD_RUST.md`。
