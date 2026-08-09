$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
. (Join-Path $PSScriptRoot "python-runtime.ps1")
$python = Resolve-AiNavPython -Root $root

& $PSScriptRoot\verify-repository-layout.ps1
if ($LASTEXITCODE -ne 0) { throw "Repository layout verification failed." }

& $python -m unittest discover -s tests -p test_production_overlay.py -v
if ($LASTEXITCODE -ne 0) { throw "Production overlay tests failed." }

& $python scripts\check-no-secrets.py --paths deploy\production scripts\verify-production-deployment.ps1 tests\test_production_overlay.py
if ($LASTEXITCODE -ne 0) { throw "Production deployment secret scan failed." }

& $PSScriptRoot\build-release-package.ps1 -ValidateOnly -PythonExecutable $python
if ($LASTEXITCODE -ne 0) { throw "Production release selection validation failed." }

git diff --check
if ($LASTEXITCODE -ne 0) { throw "Git whitespace validation failed." }

Write-Host "Production deployment preparation verification passed." -ForegroundColor Green
