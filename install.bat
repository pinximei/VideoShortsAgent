@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo.
echo ══════════════════════════════════════════════════
echo   🎬 VideoShortsAgent 一键安装脚本 (Windows)
echo ══════════════════════════════════════════════════
echo.

cd /d "%~dp0"

:: ─────────────────────────────────────────────────
:: 1. 检测 Python
:: ─────────────────────────────────────────────────
echo [1/5] 检测 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ❌ 未检测到 Python！
    echo   请先安装 Python 3.10+：https://www.python.org/downloads/
    echo   安装时 务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
    echo   ✅ Python %%v
)

:: ─────────────────────────────────────────────────
:: 2. 检测 FFmpeg
:: ─────────────────────────────────────────────────
echo [2/5] 检测 FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ❌ 未检测到 FFmpeg！
    echo.
    echo   请手动安装 FFmpeg：
    echo     1. 下载: https://github.com/BtbN/FFmpeg-Builds/releases
    echo        选择 ffmpeg-master-latest-win64-gpl.zip
    echo     2. 解压到 C:\ffmpeg
    echo     3. 把 C:\ffmpeg\bin 添加到系统 PATH 环境变量
    echo     4. 重新打开命令行，运行 ffmpeg -version 验证
    echo.
    echo   详细教程见 README.md
    echo.
    pause
    exit /b 1
)
for /f "tokens=3 delims= " %%v in ('ffmpeg -version 2^>^&1 ^| findstr /B "ffmpeg version"') do (
    echo   ✅ FFmpeg %%v
)

:: ─────────────────────────────────────────────────
:: 3. 安装 Python 依赖
:: ─────────────────────────────────────────────────
echo [3/5] 安装 Python 依赖...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo   ❌ 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)
echo   ✅ Python 依赖安装完成

:: ─────────────────────────────────────────────────
:: 4. Node.js + Remotion（可选）
:: ─────────────────────────────────────────────────
echo [4/5] 检测 Node.js（字幕动画特效，可选）...
node --version >nul 2>&1
if errorlevel 1 (
    echo   ⚠️  未检测到 Node.js，跳过 Remotion 安装
    echo   → 字幕将使用 FFmpeg ASS 静态样式（功能不受影响）
    echo   → 如需动画特效，请安装 Node.js 18+: https://nodejs.org/
) else (
    for /f "tokens=1 delims= " %%v in ('node --version 2^>^&1') do (
        echo   ✅ Node.js %%v
    )
    if exist "remotion_effects\package.json" (
        echo   安装 Remotion 特效依赖...
        pushd remotion_effects
        call npm install >nul 2>&1
        if errorlevel 1 (
            echo   ⚠️  Remotion 安装失败，将使用 ASS 字幕降级
        ) else (
            echo   ✅ Remotion 特效就绪
        )
        popd
    )
)

:: ─────────────────────────────────────────────────
:: 5. 配置 .env
:: ─────────────────────────────────────────────────
echo [5/5] 检查配置文件...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo   📝 已从 .env.example 创建 .env
        echo   ⚠️  请编辑 .env 文件，填入你的 API Key：
        echo      DASHSCOPE_API_KEY=sk-你的阿里云密钥
        echo      GROQ_API_KEY=gsk_你的Groq密钥（推荐）
    ) else (
        echo   ⚠️  未找到 .env 文件，请手动创建并填入 API Key
    )
) else (
    echo   ✅ .env 配置文件已存在
)

:: ─────────────────────────────────────────────────
:: 完成
:: ─────────────────────────────────────────────────
echo.
echo ══════════════════════════════════════════════════
echo   ✅ 安装完成！
echo ══════════════════════════════════════════════════
echo.
echo   📌 使用前请确认：
echo     1. .env 中已填入 DASHSCOPE_API_KEY
echo     2. 如需本地转录，请下载 Whisper 模型（见 README）
echo.
echo   🚀 启动方式：双击 start.bat 或运行：
echo      python -m python_agent.app
echo.
pause
