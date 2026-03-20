@echo off
setlocal enabledelayedexpansion

chcp 65001 >nul 2>&1
set "PYTHONIOENCODING=utf-8"

echo ==========================================
echo   VideoShortsAgent Launcher (ASCII-safe)
echo ==========================================

echo [1/3] Free port 7860 if in use...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7860 ^| findstr LISTENING') do (
    echo   kill PID %%a
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"
set "PYTHONPATH=%PROJECT_DIR%"

echo [0/3] Selecting Python (need pip)...
set "PY=python"
set "PY_ARGS="
"%PY%" %PY_ARGS% -m pip --version >nul 2>&1
if errorlevel 1 (
    py -3 -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: both python and py -3 cannot run pip.
        echo Run install.bat first and ensure py -3 -m pip --version works.
        pause
        exit /b 1
    )
    set "PY=py"
    set "PY_ARGS=-3"
    echo   Using: py -3
) else (
    echo   Using: python
)

echo [2/3] Check edge-tts / groq...
"%PY%" %PY_ARGS% -c "import edge_tts" >nul 2>&1
if errorlevel 1 (
    echo   pip install edge-tts...
    "%PY%" %PY_ARGS% -m pip install edge-tts
)
"%PY%" %PY_ARGS% -c "import groq" >nul 2>&1
if errorlevel 1 (
    echo   pip install groq...
    "%PY%" %PY_ARGS% -m pip install groq
)

echo [3/3] Start Gradio...
echo.
"%PY%" %PY_ARGS% -u -m python_agent.app
pause
