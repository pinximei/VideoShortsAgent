@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0.."
title AiSoul Pipeline

echo ==========================================
echo   AiSoul Pipeline 中控台
echo   启动后浏览器打开 http://127.0.0.1:8780
echo ==========================================

set "PY=py"
set "PY_ARGS=-3.12"

%PY% %PY_ARGS% -m pip install -e . -q
%PY% %PY_ARGS% scripts\start_server.py %*
