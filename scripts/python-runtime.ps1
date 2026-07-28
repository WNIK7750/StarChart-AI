function Resolve-AiNavPython {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Root
  )

  # Verification must be hermetic and must never inspect a developer's real .env.
  $env:AI_NAV_DISABLE_DOTENV = "1"

  $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
  $candidates = @()
  if ($env:AI_NAV_PYTHON) { $candidates += $env:AI_NAV_PYTHON }
  if (Test-Path -LiteralPath $venvPython) { $candidates += $venvPython }

  $venvConfig = Join-Path $Root ".venv\pyvenv.cfg"
  if (Test-Path -LiteralPath $venvConfig) {
    $configuredExecutable = Get-Content -LiteralPath $venvConfig |
      Where-Object { $_ -match "^\s*executable\s*=" } |
      Select-Object -First 1
    if ($configuredExecutable) {
      $candidates += ($configuredExecutable -replace "^\s*executable\s*=\s*", "").Trim()
    }
  }

  $pathPython = Get-Command python -CommandType Application -ErrorAction SilentlyContinue
  if ($pathPython) { $candidates += $pathPython.Source }

  foreach ($candidate in ($candidates | Select-Object -Unique)) {
    if (-not $candidate -or -not (Test-Path -LiteralPath $candidate)) { continue }
    try {
      & $candidate -c "import sys" *> $null
      if ($LASTEXITCODE -ne 0) { continue }
      $resolved = (Resolve-Path -LiteralPath $candidate).Path
      $usesProjectVenv = $resolved -eq (Resolve-Path -LiteralPath $venvPython -ErrorAction SilentlyContinue).Path
      $explicitPython = if ($env:AI_NAV_PYTHON) {
        Resolve-Path -LiteralPath $env:AI_NAV_PYTHON -ErrorAction SilentlyContinue
      } else {
        $null
      }
      $usesExplicitPython = $explicitPython -and $resolved -eq $explicitPython.Path
      $env:PYTHONPATH = "backend"
      $sitePackages = Join-Path $Root ".venv\Lib\site-packages"
      if (-not $usesProjectVenv -and -not $usesExplicitPython -and (Test-Path -LiteralPath $sitePackages)) {
        $env:PYTHONPATH = "backend$([IO.Path]::PathSeparator)$sitePackages"
      }
      return $resolved
    } catch {
      continue
    }
  }

  throw "No usable Python runtime found. Set AI_NAV_PYTHON or recreate .venv."
}
