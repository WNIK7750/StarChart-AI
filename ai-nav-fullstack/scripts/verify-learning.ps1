$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTHONPATH = "backend"
& .\.venv\Scripts\python.exe -m unittest -v `
  tests.test_learning_services `
  tests.test_content_governance `
  tests.test_platform_navigation
if ($LASTEXITCODE -ne 0) { throw "Learning unit tests failed." }

$pythonFiles = Get-ChildItem backend -Recurse -Filter *.py | ForEach-Object FullName
& .\.venv\Scripts\python.exe -m py_compile $pythonFiles
if ($LASTEXITCODE -ne 0) { throw "Python compilation failed." }

$skipSyntaxCheck = @("tool-data.js", "tool-page-lists.js")
Get-ChildItem frontend\assets\js -Filter *.js |
  Where-Object { $_.Name -notin $skipSyntaxCheck } |
  ForEach-Object {
    node --check $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "JavaScript syntax check failed: $($_.FullName)" }
  }

node --test tests\test_learning_frontend.mjs
if ($LASTEXITCODE -ne 0) { throw "Frontend learning tests failed." }

& .\.venv\Scripts\python.exe scripts\check-learning-content.py
if ($LASTEXITCODE -ne 0) { throw "Learning content validation failed." }

& .\.venv\Scripts\python.exe scripts\check-content-links.py
if ($LASTEXITCODE -ne 0) { throw "Cross-domain content link validation failed." }

& .\.venv\Scripts\python.exe scripts\benchmark-learning.py --max-p95-ms 250
if ($LASTEXITCODE -ne 0) { throw "Learning performance baseline failed." }

git diff --check
if ($LASTEXITCODE -ne 0) { throw "Git whitespace validation failed." }
Write-Host "Learning verification passed." -ForegroundColor Green
