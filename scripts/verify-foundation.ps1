$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-Verification {
  param(
    [string]$Name,
    [string]$Path
  )
  Write-Host "`n==== $Name ====" -ForegroundColor Cyan
  & $Path
  if (-not $?) { throw "$Name verification failed." }
}

Invoke-Verification "Frontend" ".\scripts\verify-frontend.ps1"
Invoke-Verification "Tools" ".\scripts\verify-tools.ps1"
Invoke-Verification "Learning and platform" ".\scripts\verify-learning.ps1"
Invoke-Verification "Users and release safety" ".\scripts\verify-users.ps1"
Invoke-Verification "HTTP test deployment" ".\scripts\verify-http-test-deployment.ps1"

Write-Host "`nNon-Agent foundation verification passed." -ForegroundColor Green
