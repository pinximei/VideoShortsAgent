@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0.."

set "PY=py"
set "PY_ARGS=-3.12"
%PY% %PY_ARGS% -m pip install -e . -q 2>nul

%PY% %PY_ARGS% scripts\run_once.py %*
if errorlevel 1 exit /b 1
