$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONPATH = "backend"
$env:PYTHONIOENCODING = "utf-8"
$python = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }

function Invoke-Step {
  param([string]$Name, [scriptblock]$Command)
  Write-Host "==> $Name"
  & $Command
  if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}

Invoke-Step "Compile Tools module" {
  & $python -m py_compile `
    backend/app/tools/repository.py `
    backend/app/tools/service.py `
    backend/app/api/v1/routers/tools.py `
    scripts/generate-tool-catalog-migration.py `
    scripts/check-content-links.py `
    tests/test_tools_services.py
}

Invoke-Step "Audit source snapshot" {
  node scripts/audit-tool-data.mjs
}

Invoke-Step "Tools service and migration tests" {
  & $python -m unittest discover -s tests -p test_tools_services.py -v
}

Invoke-Step "Frontend syntax" {
  node --check frontend/assets/js/tools-page.js
  node --check frontend/assets/js/tools-entry.js
  node --check frontend/assets/js/page-shell.js
  node --check frontend/assets/js/site-search.js
}

Invoke-Step "Whitespace check" {
  git diff --check
}
