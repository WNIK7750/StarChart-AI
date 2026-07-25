param(
  [string]$OutputPath = "",
  [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Get-ReleaseRelativePath {
  param([string]$BasePath, [string]$FullPath)
  $baseUri = [uri]($BasePath.TrimEnd("\", "/") + [IO.Path]::DirectorySeparatorChar)
  $fullUri = [uri]$FullPath
  return [uri]::UnescapeDataString($baseUri.MakeRelativeUri($fullUri).ToString()).Replace("/", "\")
}

$allowedRoots = @(
  "backend/app",
  "database/migrations",
  "frontend",
  "docs/04-operations"
)
$allowedFiles = @(
  "backend/requirements.txt",
  "backend/requirements-lock.txt",
  "backend/run.py",
  "database/schema.sql",
  "database/seed.sql",
  "database/learning_content.sql",
  "production.env.example",
  "README.md"
)
$forbiddenPattern = '(^|[\\/])(__pycache__|uploads|test-results|htmlcov|\.idea|\.workbuddy)([\\/]|$)|(\.pyc|\.pyo|\.log|\.sqlite3(|-.*)|\.coverage|\.env)$|frontend - 副本'

$files = @()
foreach ($relativeRoot in $allowedRoots) {
  $sourceRoot = Join-Path $root $relativeRoot
  if (Test-Path -LiteralPath $sourceRoot) {
    $files += Get-ChildItem -LiteralPath $sourceRoot -Recurse -File |
      Where-Object {
        $relative = Get-ReleaseRelativePath -BasePath $root -FullPath $_.FullName
        $relative -notmatch $forbiddenPattern
      }
  }
}
foreach ($relativeFile in $allowedFiles) {
  $sourceFile = Join-Path $root $relativeFile
  if (Test-Path -LiteralPath $sourceFile) {
    $files += Get-Item -LiteralPath $sourceFile
  }
}
$files = $files | Sort-Object FullName -Unique
$forbidden = @(
  $files | Where-Object {
    (Get-ReleaseRelativePath -BasePath $root -FullPath $_.FullName) -match $forbiddenPattern
  }
)
if ($forbidden.Count -gt 0) {
  throw "Release selection contains forbidden local artifacts."
}
if ($ValidateOnly) {
  [ordered]@{ passed = $true; fileCount = $files.Count; forbiddenCount = 0 } |
    ConvertTo-Json -Compress
  exit 0
}
if (-not $OutputPath) {
  throw "OutputPath is required unless ValidateOnly is used."
}
$resolvedOutput = [IO.Path]::GetFullPath((Join-Path $root $OutputPath))
if (Test-Path -LiteralPath $resolvedOutput) {
  throw "Release output already exists: $resolvedOutput"
}
$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$stageRoot = [IO.Path]::GetFullPath((Join-Path $tempBase ("ai-nav-release-" + [guid]::NewGuid().ToString("N"))))
if (-not $stageRoot.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase)) {
  throw "Invalid release staging path."
}
New-Item -ItemType Directory -Path $stageRoot | Out-Null
try {
  foreach ($file in $files) {
    $relative = Get-ReleaseRelativePath -BasePath $root -FullPath $file.FullName
    $destination = Join-Path $stageRoot $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $destination
  }
  Compress-Archive -Path (Join-Path $stageRoot "*") -DestinationPath $resolvedOutput
} finally {
  if (Test-Path -LiteralPath $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
  }
}
