@echo off
echo ==========================================
echo   VideoShortsAgent Launcher
echo ==========================================

echo [1/3] Killing old processes on port 7860...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7860 ^| findstr LISTENING') do (
    echo   Killing PID %%a
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

cd /d %~dp0

echo [2/3] Checking dependencies...
python -c "import edge_tts" >nul 2>&1
if errorlevel 1 (
    echo   Installing edge-tts...
    python -m pip install edge-tts
)
python -c "import groq" >nul 2>&1
if errorlevel 1 (
    echo   Installing groq...
    python -m pip install groq
)

echo [3/3] Starting Gradio...
echo.
python -u -m python_agent.app
pause
