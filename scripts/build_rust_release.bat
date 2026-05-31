@echo off
REM VideoShorts Studio — Rust 发布构建（需已安装 rustup: https://rustup.rs）
setlocal
cd /d "%~dp0..\rust"

where cargo >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 cargo。请先安装 Rust: https://rustup.rs
    echo        安装后重新打开终端再运行本脚本。
    exit /b 1
)

echo Building release...
cargo build --release -p vsa-gui
if errorlevel 1 exit /b 1

set "OUT=%CD%\target\release\VideoShortsStudio.exe"
echo.
echo OK: %OUT%
echo 体积约数 MB～十余 MB（不含 FFmpeg）。请随包附带 ffmpeg 或让用户自行安装。
dir "%OUT%"
pause
