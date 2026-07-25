$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
. "$PSScriptRoot\python-runtime.ps1"
$python = Resolve-AiNavPython -Root $root
$env:PYTHONUTF8 = "1"
$env:AI_NAV_PASSWORD_HASH_ROUNDS = "1000"

function Invoke-QualityStep {
  param([string]$Name, [scriptblock]$Action)
  Write-Host "==> $Name" -ForegroundColor Cyan
  & $Action
  if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}

Invoke-QualityStep "Ruff core rules" {
  & $python -m ruff check backend scripts tests --config pyproject.toml
}
Invoke-QualityStep "Python dependency audit" {
  & $python -m pip_audit -r backend\requirements.txt
}
Invoke-QualityStep "Release package exclusions" {
  & "$PSScriptRoot\build-release-package.ps1" -ValidateOnly
}
Invoke-QualityStep "Branch coverage baseline" {
  & $python -m coverage erase
  & $python -m coverage run -m unittest discover -s tests -p "test_*.py"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & $python -m coverage report --fail-under=84
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & $python -m coverage json -o docs\06-evidence\platform\coverage.json
}

Write-Host "Quality verification passed." -ForegroundColor Green
