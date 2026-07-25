$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
. (Join-Path $PSScriptRoot "python-runtime.ps1")
$python = Resolve-AiNavPython -Root $root

function Invoke-Step {
  param(
    [string]$Name,
    [scriptblock]$Command
  )
  Write-Host "==> $Name"
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE"
  }
}

Invoke-Step "Python compile users/auth modules" {
  & $python -m py_compile `
    backend/app/api/v1/routers/auth.py `
    backend/app/api/v1/routers/users.py `
    backend/app/api/v1/routers/agent.py `
    backend/app/api/v1/routers/assets.py `
    backend/app/api/v1/routers/operations.py `
    backend/app/api/v1/routers/user_learning.py `
    backend/app/api/v1/routers/privacy.py `
    backend/app/api/v1/dependencies/authorization.py `
    backend/app/users/common.py `
    backend/app/users/command_safety.py `
    backend/app/users/authentication/service.py `
    backend/app/users/authentication/rate_limit.py `
    backend/app/users/authentication/repositories/sqlite.py `
    backend/app/users/account/service.py `
    backend/app/users/account/repositories/sqlite.py `
    backend/app/users/profile/service.py `
    backend/app/users/profile/avatar.py `
    backend/app/users/profile/repositories/sqlite.py `
    backend/app/users/preferences/service.py `
    backend/app/users/preferences/facade.py `
    backend/app/users/preferences/repositories/sqlite.py `
    backend/app/users/sessions/service.py `
    backend/app/users/sessions/repositories/sqlite.py `
    backend/app/users/security/service.py `
    backend/app/users/security/repositories/sqlite.py `
    backend/app/users/authorization/service.py `
    backend/app/users/authorization/policy.py `
    backend/app/users/authorization/repositories/sqlite.py `
    backend/app/users/audit/events.py `
    backend/app/users/audit/policy.py `
    backend/app/users/audit/service.py `
    backend/app/users/audit/repositories/sqlite.py `
    backend/app/users/privacy/service.py `
    backend/app/users/privacy/repositories/sqlite.py `
    backend/app/users/assets/schemas.py `
    backend/app/users/assets/service.py `
    backend/app/users/assets/facade.py `
    backend/app/users/assets/repositories/sqlite.py `
    backend/app/users/context/facade.py `
    backend/app/agent/schemas.py `
    backend/app/agent/service.py `
    backend/app/users/observability/access.py `
    backend/app/users/observability/metrics.py `
    scripts/manage-users-backup.py `
    scripts/rehearse-users-release.py `
    scripts/build-users-acceptance-report.py `
    scripts/check-users-command-safety.py
}

Invoke-Step "Users service tests" {
  & $python -m unittest discover -s tests -p test_users_services.py -v
}

Invoke-Step "Users frontend facade tests" {
  node tests/test_users_frontend.mjs
  if ($LASTEXITCODE -ne 0) { throw "Users frontend facade tests failed with exit code $LASTEXITCODE" }
  node --check frontend/assets/js/settings.js
  if ($LASTEXITCODE -ne 0) { throw "settings.js syntax check failed with exit code $LASTEXITCODE" }
  node --check frontend/assets/js/auth-ui.js
  if ($LASTEXITCODE -ne 0) { throw "auth-ui.js syntax check failed with exit code $LASTEXITCODE" }
  node --check frontend/assets/js/users-api.js
}

Invoke-Step "Freeze auth/users contracts" {
  & $python scripts/freeze-users-contracts.py
}

Invoke-Step "Users security baseline" {
  & $python scripts/check-users-security-baseline.py
}

Invoke-Step "Users command safety coverage" {
  & $python scripts/check-users-command-safety.py
}

Invoke-Step "Users migration and backup restore rehearsal" {
  & $python scripts/rehearse-users-release.py
}

Invoke-Step "Users performance baseline" {
  & $python scripts/benchmark-users.py
}

Invoke-Step "Users final acceptance report" {
  & $python scripts/build-users-acceptance-report.py
}

Invoke-Step "Users whitespace check" {
  git diff --check
}
