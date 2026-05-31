@echo off
REM VideoShorts Studio — 单文件/单目录 EXE（勿打包任何 API Key）
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%"
set "VSA_USE_USER_CONFIG=1"

echo Building VideoShortsStudio ...
py -3 -m pip install pyinstaller pywebview -q

if not exist "resources\ffmpeg\bin\ffmpeg.exe" (
    echo [WARN] 未找到 resources\ffmpeg\bin\ffmpeg.exe
    echo        请将 FFmpeg 解压到该目录后再分发，或让用户自行安装 FFmpeg。
)

py -3 -m PyInstaller --noconfirm ^
  --name VideoShortsStudio ^
  --windowed ^
  --paths "%CD%" ^
  --hidden-import=gradio ^
  --hidden-import=python_agent.app ^
  --hidden-import=python_agent.scenarios.douyin ^
  --hidden-import=python_agent.scenarios.ecommerce ^
  --collect-submodules=gradio ^
  python_agent/desktop.py

echo.
echo 输出: dist\VideoShortsStudio\VideoShortsStudio.exe
echo 分发清单: exe + resources\ffmpeg （可选）+ 使用说明（让用户自己填 Key）
pause
