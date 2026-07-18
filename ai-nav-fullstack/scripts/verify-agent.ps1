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

Invoke-Step "Compile Agent module" {
  & $python -m py_compile `
    backend/app/agent/schemas.py `
    backend/app/agent/router.py `
    backend/app/agent/service.py `
    backend/app/agent/evaluator.py `
    backend/app/agent/tools/learning_tools.py `
    backend/app/agent/tools/catalog_tools.py `
    backend/app/api/v1/routers/agent.py `
    tests/test_agent_services.py
}

Invoke-Step "Agent service tests" {
  & $python -m unittest discover -s tests -p test_agent_services.py -v
}

Invoke-Step "Agent frontend contract" {
  node --test tests/test_agent_frontend.mjs
}

Invoke-Step "Agent frontend syntax" {
  node --check frontend/assets/js/assistant-page.js
}

Invoke-Step "Whitespace check" {
  git diff --check
}
