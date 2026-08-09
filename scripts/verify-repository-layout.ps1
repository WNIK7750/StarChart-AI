$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$errors = [System.Collections.Generic.List[string]]::new()
$requiredPaths = @(
  "backend/app",
  "backend/run.py",
  "frontend/index.html",
  "frontend/assistant.html",
  "database/migrations",
  "deploy/production/env.example",
  "deploy/production/nginx/starchart-ai.conf",
  "docs/00-index/documentation-map.md",
  "docs/00-index/repository-layout.md",
  "scripts/build-release-package.ps1",
  "tests"
)

foreach ($relativePath in $requiredPaths) {
  if (-not (Test-Path -LiteralPath (Join-Path $root $relativePath))) {
    $errors.Add("Missing canonical path: $relativePath")
  }
}

foreach ($retiredPath in @("frontend - 副本", "full-stack-analysis", "production.env.example")) {
  if (Test-Path -LiteralPath (Join-Path $root $retiredPath)) {
    $errors.Add("Retired root path still exists: $retiredPath")
  }
}

$migrationFiles = @(Get-ChildItem -LiteralPath (Join-Path $root "database/migrations") -File -Filter "*.sql" | Sort-Object Name)
$migrationNumbers = @()
foreach ($migration in $migrationFiles) {
  if ($migration.Name -notmatch '^(\d{3})_[a-z0-9_]+\.sql$') {
    $errors.Add("Invalid migration filename: $($migration.Name)")
    continue
  }
  $migrationNumbers += [int]$Matches[1]
}
for ($index = 0; $index -lt $migrationNumbers.Count; $index++) {
  $expected = $index + 1
  if ($migrationNumbers[$index] -ne $expected) {
    $errors.Add("Migration sequence is not contiguous at expected number $expected")
    break
  }
}

$tracked = @(& git ls-files)
if ($LASTEXITCODE -ne 0) {
  $errors.Add("Unable to inspect tracked files")
} else {
  $forbiddenTrackedPatterns = @(
    '(^|/)(__pycache__|uploads|test-results|release)(/|$)',
    '(^|/)(frontend - 副本|full-stack-analysis)(/|$)',
    '(^|/)(\.coverage|[^/]+\.log|\.tmp_[^/]+\.txt)$',
    '(^|/)database/[^/]+\.sqlite3(?:-.+)?$'
  )
  foreach ($relativePath in $tracked) {
    foreach ($pattern in $forbiddenTrackedPatterns) {
      if ($relativePath -match $pattern) {
        $errors.Add("Tracked runtime or retired file: $relativePath")
        break
      }
    }
  }
}

if ($errors.Count -gt 0) {
  $errors | ForEach-Object { Write-Error $_ }
  throw "Repository layout verification failed with $($errors.Count) issue(s)."
}

[ordered]@{
  passed = $true
  canonicalPathCount = $requiredPaths.Count
  migrationCount = $migrationFiles.Count
  productionTemplate = "deploy/production/env.example"
  retiredRootPathCount = 0
  forbiddenTrackedFileCount = 0
} | ConvertTo-Json -Compress
