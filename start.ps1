param(
  [switch]$NoPause,
  [switch]$Restart,
  [switch]$Stop
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$venvRoot = Join-Path $root ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$requirementsPath = Join-Path $root "backend\requirements.txt"
$script:stage = "initialization"

$sha256 = [Security.Cryptography.SHA256]::Create()
try {
  $rootBytes = [Text.Encoding]::UTF8.GetBytes($root.ToLowerInvariant())
  $rootKey = (
    [BitConverter]::ToString($sha256.ComputeHash($rootBytes))
  ).Replace("-", "").Substring(0, 16).ToLowerInvariant()
} finally {
  $sha256.Dispose()
}

$localAppData = [Environment]::GetFolderPath(
  [Environment+SpecialFolder]::LocalApplicationData
)
if ([string]::IsNullOrWhiteSpace($localAppData)) {
  throw "Unable to resolve the local application data directory."
}
$launcherRoot = Join-Path (Join-Path $localAppData "AI-Nav\launcher") $rootKey
$statePath = Join-Path $launcherRoot "state.json"
$stdoutPath = Join-Path $launcherRoot "stdout.log"
$stderrPath = Join-Path $launcherRoot "stderr.log"
$requirementsHashPath = Join-Path $launcherRoot "requirements.sha256"
[void][IO.Directory]::CreateDirectory($launcherRoot)

if ([string]::IsNullOrWhiteSpace($env:AI_NAV_AGENT_GUEST_CHAT_ENABLED)) {
  $env:AI_NAV_AGENT_GUEST_CHAT_ENABLED = "1"
}
if ([string]::IsNullOrWhiteSpace($env:AI_NAV_AGENT_SESSIONS_ENABLED)) {
  $env:AI_NAV_AGENT_SESSIONS_ENABLED = "1"
}
if ([string]::IsNullOrWhiteSpace($env:AI_NAV_AGENT_PROVIDER_LIVE_ENABLED)) {
  $env:AI_NAV_AGENT_PROVIDER_LIVE_ENABLED = "0"
}

function Test-PythonCommand {
  param(
    [string]$FilePath,
    [string[]]$PrefixArguments = @()
  )

  if (-not $FilePath -or -not (Test-Path -LiteralPath $FilePath)) {
    return $false
  }

  try {
    $arguments = @($PrefixArguments) + @(
      "-c",
      "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
    )
    & $FilePath @arguments *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

function Resolve-BasePython {
  $candidates = @()

  if ($env:AI_NAV_PYTHON) {
    $candidates += [pscustomobject]@{
      FilePath = $env:AI_NAV_PYTHON
      PrefixArguments = @()
    }
  }

  $venvConfig = Join-Path $venvRoot "pyvenv.cfg"
  if (Test-Path -LiteralPath $venvConfig) {
    $configuredExecutable = Get-Content -LiteralPath $venvConfig |
      Where-Object { $_ -match "^\s*executable\s*=" } |
      Select-Object -First 1
    if ($configuredExecutable) {
      $candidates += [pscustomobject]@{
        FilePath = ($configuredExecutable -replace "^\s*executable\s*=\s*", "").Trim()
        PrefixArguments = @()
      }
    }
  }

  $pathPython = Get-Command python -CommandType Application -ErrorAction SilentlyContinue
  if ($pathPython) {
    $candidates += [pscustomobject]@{
      FilePath = $pathPython.Source
      PrefixArguments = @()
    }
  }

  $pathLauncher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue
  if ($pathLauncher) {
    $candidates += [pscustomobject]@{
      FilePath = $pathLauncher.Source
      PrefixArguments = @("-3")
    }
  }

  foreach ($candidate in $candidates) {
    if (Test-PythonCommand $candidate.FilePath $candidate.PrefixArguments) {
      return $candidate
    }
  }

  throw "Python 3.11+ was not found. Install Python or set AI_NAV_PYTHON."
}

function Invoke-CheckedProcess {
  param(
    [string]$Stage,
    [string]$FilePath,
    [string[]]$Arguments = @()
  )

  try {
    & $FilePath @Arguments
    $exitCode = $LASTEXITCODE
  } catch {
    throw "$Stage failed: $($_.Exception.Message)"
  }
  if ($exitCode -ne 0) {
    throw "$Stage failed with exit code $exitCode."
  }
}

function Test-ExistingAiNav {
  try {
    $health = Invoke-RestMethod `
      -Uri "http://127.0.0.1:8088/api/v1/health" `
      -TimeoutSec 3
    $runtime = Invoke-RestMethod `
      -Uri "http://127.0.0.1:8088/api/v1/runtime/public" `
      -TimeoutSec 3
    return (
      $health.status -eq "ok" -and
      -not [string]::IsNullOrWhiteSpace([string]$runtime.deploymentProfile) -and
      $runtime.agent.guestChat -eq $true -and
      (
        $env:AI_NAV_AGENT_SESSIONS_ENABLED -ne "1" -or
        $runtime.agent.authenticatedSessions -eq $true
      )
    )
  } catch {
    return $false
  }
}

function Wait-AiNavReady {
  param([int]$TimeoutSeconds = 30)

  $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
  while ([DateTime]::UtcNow -lt $deadline) {
    if (Test-ExistingAiNav) {
      return $true
    }
    Start-Sleep -Milliseconds 500
  }
  return $false
}

function Test-LocalPortOccupied {
  $client = New-Object Net.Sockets.TcpClient
  try {
    $connection = $client.ConnectAsync("127.0.0.1", 8088)
    if (-not $connection.Wait(1000)) {
      return $false
    }
    return $client.Connected
  } catch {
    return $false
  } finally {
    $client.Dispose()
  }
}

function Remove-StaleState {
  if (Test-Path -LiteralPath $statePath) {
    Remove-Item -LiteralPath $statePath -Force
  }
  $script:ManagedProcess = $null
  $script:ManagedState = $null
}

function Test-ManagedProcess {
  $script:ManagedProcess = $null
  $script:ManagedState = $null
  if (-not (Test-Path -LiteralPath $statePath)) {
    return $false
  }

  try {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if (
      -not [StringComparer]::OrdinalIgnoreCase.Equals([string]$state.root, $root) -or
      -not [StringComparer]::OrdinalIgnoreCase.Equals(
        [string]$state.pythonPath,
        $venvPython
      ) -or
      [int]$state.port -ne 8088 -or
      [int]$state.processId -le 0
    ) {
      Remove-StaleState
      return $false
    }

    $process = Get-CimInstance Win32_Process `
      -Filter "ProcessId = $([int]$state.processId)" `
      -ErrorAction Stop
    if (-not $process) {
      Remove-StaleState
      return $false
    }

    $expectedName = [IO.Path]::GetFileName($venvPython)
    $creationFormat = "yyyy-MM-ddTHH:mm:ss.ffffff"
    $expectedCreated = ([DateTime]$state.creationTime).ToString($creationFormat)
    $actualCreated = ([DateTime]$process.CreationDate).ToString($creationFormat)
    $commandLine = [string]$process.CommandLine
    if (
      -not [StringComparer]::OrdinalIgnoreCase.Equals(
        [string]$process.Name,
        $expectedName
      ) -or
      -not [StringComparer]::OrdinalIgnoreCase.Equals(
        [string]$process.ExecutablePath,
        $venvPython
      ) -or
      $actualCreated -ne $expectedCreated -or
      $commandLine.IndexOf("backend\run.py", [StringComparison]::OrdinalIgnoreCase) -lt 0
    ) {
      Remove-StaleState
      return $false
    }

    $script:ManagedProcess = $process
    $script:ManagedState = $state
    return $true
  } catch {
    Remove-StaleState
    return $false
  }
}

function Get-DescendantProcessIds {
  param([int]$ParentProcessId)

  $result = @()
  $children = Get-CimInstance Win32_Process `
    -Filter "ParentProcessId = $ParentProcessId" `
    -ErrorAction SilentlyContinue
  foreach ($child in $children) {
    $result += @(Get-DescendantProcessIds -ParentProcessId $child.ProcessId)
    $result += [int]$child.ProcessId
  }
  return $result
}

function Stop-ManagedService {
  if (-not (Test-ManagedProcess)) {
    if (Test-LocalPortOccupied) {
      throw "Port 8088 is owned by an unmanaged process; refusing to stop it."
    }
    Write-Host "The local service is not running." -ForegroundColor Yellow
    return
  }

  $parentId = [int]$script:ManagedState.processId
  $descendants = @(Get-DescendantProcessIds -ParentProcessId $parentId)
  foreach ($processId in $descendants) {
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
  }
  Stop-Process -Id $parentId -Force -ErrorAction SilentlyContinue

  $deadline = [DateTime]::UtcNow.AddSeconds(10)
  while ([DateTime]::UtcNow -lt $deadline) {
    if (-not (Get-Process -Id $parentId -ErrorAction SilentlyContinue)) {
      break
    }
    Start-Sleep -Milliseconds 200
  }
  Remove-StaleState
  Write-Host "AI Nav has stopped." -ForegroundColor Green
}

function Ensure-VirtualEnvironment {
  if (Test-PythonCommand $venvPython) {
    return $false
  }

  $basePython = Resolve-BasePython
  $resolvedVenv = [IO.Path]::GetFullPath($venvRoot)
  if (
    [IO.Path]::GetDirectoryName($resolvedVenv) -ne $root -or
    [IO.Path]::GetFileName($resolvedVenv) -ne ".venv"
  ) {
    throw "Refusing to modify a virtual environment outside this project."
  }

  if (Test-Path -LiteralPath $venvRoot) {
    Write-Host "The project virtual environment is invalid; rebuilding it..." -ForegroundColor Yellow
    Remove-Item -LiteralPath $venvRoot -Recurse -Force
  }

  $script:stage = "rebuilding virtual environment"
  $createArguments = @($basePython.PrefixArguments) + @("-m", "venv", $venvRoot)
  Invoke-CheckedProcess $script:stage $basePython.FilePath $createArguments
  if (-not (Test-PythonCommand $venvPython)) {
    throw "The new virtual environment could not start."
  }
  return $true
}

function Ensure-Dependencies {
  param([bool]$ForceInstall)

  $currentHash = (Get-FileHash -LiteralPath $requirementsPath -Algorithm SHA256).Hash
  $storedHash = ""
  if (Test-Path -LiteralPath $requirementsHashPath) {
    $storedHash = (Get-Content -LiteralPath $requirementsHashPath -Raw).Trim()
  }
  if (-not $ForceInstall -and $storedHash -eq $currentHash) {
    Write-Host "Dependencies are unchanged; skipping installation." -ForegroundColor DarkGray
    return
  }

  $script:stage = "installing dependencies"
  Invoke-CheckedProcess $script:stage $venvPython @(
    "-m",
    "pip",
    "install",
    "-r",
    $requirementsPath
  )
  Set-Content -LiteralPath $requirementsHashPath -Value $currentHash -Encoding Ascii
}

function Write-LauncherState {
  param([Diagnostics.Process]$Process)

  $processInfo = $null
  $deadline = [DateTime]::UtcNow.AddSeconds(5)
  while (-not $processInfo -and [DateTime]::UtcNow -lt $deadline) {
    $processInfo = Get-CimInstance Win32_Process `
      -Filter "ProcessId = $($Process.Id)" `
      -ErrorAction SilentlyContinue
    if (-not $processInfo) {
      Start-Sleep -Milliseconds 100
    }
  }
  if (-not $processInfo) {
    throw "Unable to read the new service process information."
  }

  $state = [ordered]@{
    root = $root
    processId = [int]$Process.Id
    creationTime = ([DateTime]$processInfo.CreationDate).ToString(
      "yyyy-MM-ddTHH:mm:ss.ffffff"
    )
    pythonPath = $venvPython
    port = 8088
  }
  $stateJson = $state | ConvertTo-Json
  $utf8WithBom = New-Object Text.UTF8Encoding($true)
  [IO.File]::WriteAllText($statePath, $stateJson, $utf8WithBom)
}

function Start-ManagedService {
  if (Test-ManagedProcess) {
    if (Test-ExistingAiNav) {
      Write-Host "AI Nav is already running: http://127.0.0.1:8088/" -ForegroundColor Green
      return
    }
    Write-Host "The managed service is unhealthy; redeploying..." -ForegroundColor Yellow
    Stop-ManagedService
  } elseif (Test-LocalPortOccupied) {
    throw "Port 8088 is owned by an unmanaged process; it was not stopped or replaced."
  }

  $script:stage = "checking virtual environment"
  $venvRebuilt = Ensure-VirtualEnvironment
  Ensure-Dependencies -ForceInstall $venvRebuilt

  foreach ($logPath in ($stdoutPath, $stderrPath)) {
    if (Test-Path -LiteralPath $logPath) {
      Remove-Item -LiteralPath $logPath -Force
    }
  }

  $script:stage = "starting application"
  Write-Host "Deploying AI Nav: http://127.0.0.1:8088/" -ForegroundColor Cyan
  $process = Start-Process `
    -FilePath $venvPython `
    -ArgumentList @("backend\run.py") `
    -WorkingDirectory $root `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath `
    -WindowStyle Hidden `
    -PassThru
  Write-LauncherState -Process $process

  if (-not (Wait-AiNavReady -TimeoutSeconds 30)) {
    Stop-ManagedService
    throw "The application was not ready within 30 seconds. Log: $stderrPath"
  }
  Write-Host "Deployment complete: http://127.0.0.1:8088/" -ForegroundColor Green
  Write-Host "Log directory: $launcherRoot" -ForegroundColor DarkGray
}

function Show-ControlMenu {
  while ($true) {
    Write-Host ""
    if ((Test-ManagedProcess) -and (Test-ExistingAiNav)) {
      Write-Host "Status: running  http://127.0.0.1:8088/" -ForegroundColor Green
    } elseif (Test-LocalPortOccupied) {
      Write-Host "Status: port 8088 is owned by an unmanaged process" -ForegroundColor Red
    } else {
      Write-Host "Status: stopped" -ForegroundColor Yellow
    }

    $choice = Read-Host "[R] Redeploy  [S] Stop service  [Q] Exit controller  [Enter] Refresh"
    switch ($choice.Trim().ToUpperInvariant()) {
      "R" {
        if (Test-ManagedProcess) {
          Stop-ManagedService
        } elseif (Test-LocalPortOccupied) {
          Write-Host "Redeploy refused: port 8088 is not owned by this launcher." -ForegroundColor Red
          continue
        }
        Start-ManagedService
      }
      "S" {
        try {
          Stop-ManagedService
        } catch {
          Write-Host $_.Exception.Message -ForegroundColor Red
        }
      }
      "Q" {
        Write-Host "Controller exited; the service keeps its current state." -ForegroundColor DarkGray
        return
      }
      default {
        continue
      }
    }
  }
}

try {
  if ($Stop) {
    $script:stage = "stopping application"
    Stop-ManagedService
    return
  }

  if ($Restart) {
    $script:stage = "redeploying"
    if (Test-ManagedProcess) {
      Stop-ManagedService
    } elseif (Test-LocalPortOccupied) {
      throw "Port 8088 is not owned by this launcher; redeploy refused."
    }
  }

  Start-ManagedService
  if ($NoPause) {
    return
  }
  Show-ControlMenu
  return
} catch {
  Write-Host "One-click deployment failed during: $script:stage" -ForegroundColor Red
  Write-Host $_.Exception.Message -ForegroundColor Red
  Write-Host "Log directory: $launcherRoot" -ForegroundColor DarkGray
  if (-not $NoPause) {
    Read-Host "Press Enter to close"
  }
  exit 1
}
