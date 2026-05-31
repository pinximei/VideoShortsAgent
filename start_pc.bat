@echo off
setlocal
chcp 65001 >nul 2>&1
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
set "PYTHONPATH=%CD%"

echo ==========================================
set VSA_USE_USER_CONFIG=1
echo   VideoShorts Studio (PC)
echo ==========================================

set "PY=python"
set "PY_ARGS="
"%PY%" %PY_ARGS% -m pip --version >nul 2>&1
if errorlevel 1 (
    set "PY=py"
    set "PY_ARGS=-3"
)

"%PY%" %PY_ARGS% -m pip install pywebview -q 2>nul

"%PY%" %PY_ARGS% -u -m python_agent.desktop
if errorlevel 1 pause
