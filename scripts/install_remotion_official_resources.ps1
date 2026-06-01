# 安装 Remotion 官方资源（skills + npm 包 + MCP 说明）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "[1/3] sync vendor/remotion-best-practices ..."
Set-Location $Root
py -3 scripts/sync_remotion_official_skills.py

Write-Host "[2/3] remotion_effects npm packages ..."
Set-Location "$Root\remotion_effects"
npm install
npx remotion add @remotion/transitions 2>$null

Write-Host "[3/3] 完成。MCP 已写入 .cursor/mcp.json；文档: docs/REMOTION_OFFICIAL_RESOURCES.md"
