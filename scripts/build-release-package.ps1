param(
  [string]$OutputPath = "",
  [string]$PythonExecutable = "",
  [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $PythonExecutable) {
  $venvPython = Join-Path $root ".venv/Scripts/python.exe"
  if (Test-Path -LiteralPath $venvPython) {
    $PythonExecutable = $venvPython
  } else {
    $pythonCommand = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
      $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    }
    if (-not $pythonCommand) {
      throw "Python is required to scan release content."
    }
    $PythonExecutable = $pythonCommand.Source
  }
}

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
  "docs/04-operations",
  "deploy/http-test"
)
$allowedFiles = @(
  "backend/requirements.txt",
  "backend/requirements-lock.txt",
  "backend/run.py",
  "database/schema.sql",
  "database/seed.sql",
  "database/learning_content.sql",
  "scripts/check-no-secrets.py",
  "scripts/provision-http-test-account.py",
  "production.env.example",
  "README.md"
)
$forbiddenPattern = '(^|[\\/])(__pycache__|uploads|test-results|htmlcov|\.idea|\.workbuddy)([\\/]|$)|(\.pyc|\.pyo|\.log|\.sqlite3(|-.*)|\.coverage|\.env)$|frontend - 副本'

$excludedPattern = '(^|[\\/])(__pycache__|test-results|htmlcov|\.idea|\.workbuddy)([\\/]|$)|(\.pyc|\.pyo|\.coverage)$'
$sensitivePattern = '(^|[\\/])(uploads|logs?|backups?)([\\/]|$)|(\.log|\.sqlite3(|-.*)|\.sqlite|\.db|\.bak|\.backup|\.old|\.orig|\.dump|\.zip|\.7z|\.tar|\.tar\.gz|\.sql\.gz)$|(^|[\\/])[^\\/]*(backup|dump)[^\\/]*$|(^|[\\/])[^\\/]*provider[^\\/]*(response|evidence)[^\\/]*$|(^|[\\/])[^\\/]*(response|evidence)[^\\/]*provider[^\\/]*$'

function Test-EnvironmentTemplate {
  param([string]$RelativePath)
  $leaf = Split-Path -Leaf $RelativePath
  return $leaf -eq "env.example" -or $leaf.EndsWith(".env.example", [StringComparison]::OrdinalIgnoreCase)
}

function Test-ForbiddenReleasePath {
  param([string]$RelativePath)
  $leaf = Split-Path -Leaf $RelativePath
  if (($leaf -eq ".env" -or $leaf -match '(?i)\.env($|\.)') -and -not (Test-EnvironmentTemplate $RelativePath)) {
    return $true
  }
  return $RelativePath -match $sensitivePattern
}

$files = @()
foreach ($relativeRoot in $allowedRoots) {
  $sourceRoot = Join-Path $root $relativeRoot
  if (Test-Path -LiteralPath $sourceRoot) {
    $rootFiles = @(Get-ChildItem -LiteralPath $sourceRoot -Recurse -File)
    $forbidden = @(
      $rootFiles | Where-Object {
        $relative = Get-ReleaseRelativePath -BasePath $root -FullPath $_.FullName
        Test-ForbiddenReleasePath $relative
      }
    )
    if ($forbidden.Count -gt 0) {
      throw "Release selection contains forbidden secrets, runtime data, logs, backups, or provider evidence."
    }
    $files += $rootFiles | Where-Object {
      $relative = Get-ReleaseRelativePath -BasePath $root -FullPath $_.FullName
      $relative -notmatch $excludedPattern -and $relative -notmatch $forbiddenPattern
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
    $relative = Get-ReleaseRelativePath -BasePath $root -FullPath $_.FullName
    Test-ForbiddenReleasePath $relative
  }
)
if ($forbidden.Count -gt 0) {
  throw "Release selection contains forbidden secrets, runtime data, logs, backups, or provider evidence."
}

function Invoke-ReleaseSecretScan {
  param(
    [string]$ScanRoot,
    [System.IO.FileInfo[]]$SelectedFiles
  )
  $scanner = Join-Path $ScanRoot "scripts/check-no-secrets.py"
  if (-not (Test-Path -LiteralPath $scanner)) {
    throw "Release secret scanner is missing."
  }
  $scanPaths = @($SelectedFiles | ForEach-Object { $_.FullName })
  $pathList = [IO.Path]::GetTempFileName()
  try {
    [IO.File]::WriteAllLines($pathList, $scanPaths, [Text.UTF8Encoding]::new($false))
    Push-Location $ScanRoot
    try {
      $scanOutput = @(
        & $PythonExecutable $scanner --paths-file $pathList --allow-release-assets 2>&1
      )
      if ($LASTEXITCODE -ne 0) {
        $safeDetails = ($scanOutput -join [Environment]::NewLine)
        throw "Release content scan failed.`n${safeDetails}"
      }
    } finally {
      Pop-Location
    }
  } finally {
    Remove-Item -LiteralPath $pathList -Force -ErrorAction SilentlyContinue
  }
}

Invoke-ReleaseSecretScan -ScanRoot $root -SelectedFiles $files

if ($ValidateOnly) {
  $deploymentOverlayCount = @(
    $files | Where-Object {
      (Get-ReleaseRelativePath -BasePath $root -FullPath $_.FullName) -like "deploy\http-test\*"
    }
  ).Count
  [ordered]@{
    passed = $true
    fileCount = $files.Count
    forbiddenCount = 0
    deploymentOverlayCount = $deploymentOverlayCount
  } |
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
  $stagedFiles = @(Get-ChildItem -LiteralPath $stageRoot -Recurse -File)
  Invoke-ReleaseSecretScan -ScanRoot $stageRoot -SelectedFiles $stagedFiles
  Compress-Archive -Path (Join-Path $stageRoot "*") -DestinationPath $resolvedOutput
} finally {
  if (Test-Path -LiteralPath $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
  }
}
