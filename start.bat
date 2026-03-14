@echo off
echo ==========================================
echo   VideoShortsAgent Launcher
echo ==========================================

echo [1/2] Killing old processes on port 7860...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7860 ^| findstr LISTENING') do (
    echo   Killing PID %%a
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

cd /d %~dp0

echo [2/2] Starting Gradio...
echo.
python -u -m python_agent.app
pause
