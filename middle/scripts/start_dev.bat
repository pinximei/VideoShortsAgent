@echo off
REM 开发：后端 8780 + 前端 Vite 5174（代理 /api）
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0.."

start "pipeline-api" cmd /k py -3.12 scripts\start_server.py
cd frontend
if not exist node_modules call npm install
start "pipeline-ui" cmd /k npm run dev
echo API http://127.0.0.1:8780  UI http://127.0.0.1:5174
