# Aimiguan 开发环境一键启动脚本
# 功能：初始化数据库 + 启动后端 + 启动前端

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          Aimiguan 开发环境启动脚本 v1.0                    ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "🔍 检查 Python 环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# 检查 Node.js
Write-Host "🔍 检查 Node.js 环境..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✓ Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ 未找到 Node.js，请先安装 Node.js 16+" -ForegroundColor Red
    exit 1
}

# 初始化后端
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📦 初始化后端..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

Set-Location "$ProjectRoot\backend"

# 检查并安装依赖
if (-not (Test-Path "venv")) {
    Write-Host "🔧 创建虚拟环境..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "🔧 激活虚拟环境..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

Write-Host "🔧 安装/更新依赖..." -ForegroundColor Yellow
pip install -r requirements.txt -q

# 初始化数据库
Write-Host "🗄️  初始化数据库..." -ForegroundColor Yellow
if (Test-Path "init_db.py") {
    python init_db.py
    Write-Host "✓ 数据库初始化完成" -ForegroundColor Green
} else {
    Write-Host "⚠️  未找到 init_db.py，跳过数据库初始化" -ForegroundColor Yellow
}

# 初始化前端
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📦 初始化前端..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

Set-Location "$ProjectRoot\frontend"

if (-not (Test-Path "node_modules")) {
    Write-Host "🔧 安装前端依赖..." -ForegroundColor Yellow
    npm install
} else {
    Write-Host "✓ 前端依赖已安装" -ForegroundColor Green
}

# 启动服务
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🚀 启动服务..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "📌 后端服务: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📌 API 文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "📌 前端服务: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 提示: 按 Ctrl+C 停止所有服务" -ForegroundColor Yellow
Write-Host ""

# 启动后端（后台）
Set-Location "$ProjectRoot\backend"
$backendJob = Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    & ".\venv\Scripts\Activate.ps1"
    python main.py
} -ArgumentList (Get-Location).Path

# 等待后端启动
Start-Sleep -Seconds 3

# 启动前端（前台）
Set-Location "$ProjectRoot\frontend"
try {
    npm run dev
} finally {
    # 清理：停止后端任务
    Write-Host ""
    Write-Host "🛑 正在停止服务..." -ForegroundColor Yellow
    Stop-Job -Job $backendJob
    Remove-Job -Job $backendJob
    Write-Host "✓ 服务已停止" -ForegroundColor Green
}
