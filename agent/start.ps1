$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[清理] 检查 8000 端口..." -ForegroundColor Cyan
$pids = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
foreach ($pid in $pids) {
    Write-Host "[清理] 结束进程 $pid" -ForegroundColor Yellow
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
}

Write-Host "[启动] ai-nav 后端..." -ForegroundColor Green
& "$PSScriptRoot\venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
