$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. (Join-Path $PSScriptRoot "python-runtime.ps1")
$python = Resolve-AiNavPython -Root $root
$runId = [Guid]::NewGuid().ToString("N")
$resultRoot = Join-Path ([IO.Path]::GetTempPath()) "ai-nav-http-test-$runId"
$databasePath = Join-Path $resultRoot "gate.sqlite3"
$manifestPath = Join-Path $root "docs\06-evidence\platform\http-test-deployment-manifest.json"
$env:AI_NAV_DISABLE_DOTENV = "1"
$env:AI_NAV_PASSWORD_HASH_ROUNDS = "1000"
$env:AI_NAV_DATABASE_PATH = $databasePath
$env:PYTHONPATH = "backend$([IO.Path]::PathSeparator)tests"

function New-StructuredResult {
  param(
    [string]$Name,
    [bool]$Passed,
    [int]$Count,
    [DateTime]$StartedAt
  )
  $payload = [ordered]@{
    schemaVersion = 1
    runId = $runId
    name = $Name
    passed = $Passed
    count = $Count
    startedAt = $StartedAt.ToUniversalTime().ToString("o").Replace("+00:00", "Z")
    finishedAt = [DateTime]::UtcNow.ToString("o").Replace("+00:00", "Z")
  }
  $payload |
    ConvertTo-Json -Depth 3 |
    Set-Content -LiteralPath (Join-Path $resultRoot "$Name.json") -Encoding utf8
}

function Invoke-PythonTestCheck {
  param(
    [string]$Name,
    [string[]]$Modules
  )
  Write-Host "`n==== HTTP test deployment: $Name ====" -ForegroundColor Cyan
  $startedAt = [DateTime]::UtcNow
  $previousPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $lines = @(& $python -m unittest @Modules -v 2>&1)
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousPreference
  }
  $lines | ForEach-Object { Write-Host $_ }
  $rendered = $lines -join "`n"
  $match = [regex]::Match($rendered, "Ran\s+(\d+)\s+tests?")
  $count = if ($match.Success) { [int]$match.Groups[1].Value } else { 0 }
  New-StructuredResult $Name ($exitCode -eq 0 -and $match.Success) $count $startedAt
  if ($exitCode -ne 0 -or -not $match.Success) {
    throw "$Name check failed; previous passing evidence was not replaced."
  }
}

function Invoke-NodeTestCheck {
  param(
    [string]$Name,
    [string[]]$Files
  )
  Write-Host "`n==== HTTP test deployment: $Name ====" -ForegroundColor Cyan
  $startedAt = [DateTime]::UtcNow
  $previousPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $lines = @(node --test @Files 2>&1)
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousPreference
  }
  $lines | ForEach-Object { Write-Host $_ }
  $rendered = $lines -join "`n"
  $match = [regex]::Match(
    $rendered,
    "(?m)^[^\r\n]*\btests\s+(\d+)\s*$"
  )
  $count = if ($match.Success) { [int]$match.Groups[1].Value } else { 0 }
  New-StructuredResult $Name ($exitCode -eq 0 -and $match.Success) $count $startedAt
  if ($exitCode -ne 0 -or -not $match.Success) {
    throw "$Name check failed; previous passing evidence was not replaced."
  }
}

New-Item -ItemType Directory -Path $resultRoot -Force | Out-Null
try {
  & $python -c "from app.db.database import initialize_database; initialize_database()"
  if ($LASTEXITCODE -ne 0) {
    throw "Temporary gate database initialization failed."
  }

  Invoke-PythonTestCheck "runtime" @(
    "tests.test_http_test_runtime",
    "tests.test_agent_provider"
  )
  Invoke-PythonTestCheck "policy" @(
    "tests.test_http_test_policy"
  )
  Invoke-PythonTestCheck "agentHistory" @(
    "tests.test_agent_sessions",
    "tests.test_agent_provider",
    "tests.test_agent_services",
    "tests.test_agent_replay"
  )
  Invoke-PythonTestCheck "guestAgent" @(
    "tests.test_agent_guest",
    "tests.test_agent_services",
    "tests.test_agent_observability"
  )
  Invoke-NodeTestCheck "frontend" @(
    "tests/test_public_path.mjs",
    "tests/test_frontend_api.mjs",
    "tests/test_auth_ui.mjs",
    "tests/test_users_frontend.mjs",
    "tests/test_frontend_url_safety.mjs",
    "tests/test_frontend_entries.mjs",
    "tests/test_guest_agent_memory.mjs",
    "tests/test_agent_frontend.mjs",
    "tests/test_agent_sse.mjs",
    "tests/test_frontend_performance.mjs",
    "tests/test_interaction_performance.mjs",
    "tests/test_learning_frontend.mjs",
    "tests/test_http_static_performance.mjs"
  )
  Invoke-PythonTestCheck "overlay" @(
    "tests.test_provision_http_test_account",
    "tests.test_http_test_overlay"
  )

  Write-Host "`n==== HTTP test deployment: release ====" -ForegroundColor Cyan
  $releaseStartedAt = [DateTime]::UtcNow
  $previousPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $releaseLines = @(
      & $python -m unittest tests.test_release_http_test_overlay -v 2>&1
    )
    $releaseExitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousPreference
  }
  $releaseLines | ForEach-Object { Write-Host $_ }
  $releaseRendered = $releaseLines -join "`n"
  $releaseMatch = [regex]::Match($releaseRendered, "Ran\s+(\d+)\s+tests?")
  $releaseCount = if ($releaseMatch.Success) {
    [int]$releaseMatch.Groups[1].Value
  } else {
    0
  }
  if ($releaseExitCode -eq 0 -and $releaseMatch.Success) {
    & ".\scripts\build-release-package.ps1" -ValidateOnly
    $releaseExitCode = $LASTEXITCODE
  }
  if ($releaseExitCode -eq 0) {
    & $python scripts/check-no-secrets.py --paths `
      deploy/http-test `
      scripts/build-release-package.ps1
    $releaseExitCode = $LASTEXITCODE
  }
  New-StructuredResult "release" ($releaseExitCode -eq 0) $releaseCount $releaseStartedAt
  if ($releaseExitCode -ne 0 -or -not $releaseMatch.Success) {
    throw "release check failed; previous passing evidence was not replaced."
  }

  $sourceCommit = "WORKTREE"
  $status = @(git status --porcelain)
  if ($LASTEXITCODE -eq 0 -and $status.Count -eq 0) {
    $candidateCommit = (git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -eq 0 -and $candidateCommit -match "^[0-9a-f]{40}$") {
      $sourceCommit = $candidateCommit
    }
  }
  & $python scripts/build-http-test-deployment-manifest.py `
    --results-dir $resultRoot `
    --run-id $runId `
    --output $manifestPath `
    --source-commit $sourceCommit
  if ($LASTEXITCODE -ne 0) {
    throw "HTTP test deployment manifest generation failed."
  }
} finally {
  if (Test-Path -LiteralPath $resultRoot) {
    Remove-Item -LiteralPath $resultRoot -Recurse -Force
  }
}

Write-Host "`nHTTP test deployment verification passed." -ForegroundColor Green
