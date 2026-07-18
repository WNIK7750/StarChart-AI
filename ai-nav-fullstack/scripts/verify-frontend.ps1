$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> Frontend entry contract"
node --test tests/test_frontend_entries.mjs tests/test_frontend_api.mjs tests/test_frontend_url_safety.mjs tests/test_frontend_feedback.mjs tests/test_auth_ui.mjs
if ($LASTEXITCODE -ne 0) { throw "Frontend entry contract failed." }

Write-Host "==> Frontend syntax"
$skipSyntaxCheck = @("tool-data.js", "tool-page-lists.js")
Get-ChildItem frontend/assets/js -Filter *.js |
  Where-Object { $_.Name -notin $skipSyntaxCheck } |
  ForEach-Object {
    node --check $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "JavaScript syntax check failed: $($_.FullName)" }
  }

Write-Host "==> Whitespace check"
git diff --check
if ($LASTEXITCODE -ne 0) { throw "Git whitespace validation failed." }
Write-Host "Frontend verification passed." -ForegroundColor Green
