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
$script:stage = "初始化"

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
  throw "无法解析本机应用数据目录。"
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

  throw "未找到可用的 Python。请安装 Python 3.11+，或设置 AI_NAV_PYTHON。"
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
    throw "$Stage 失败：$($_.Exception.Message)"
  }
  if ($exitCode -ne 0) {
    throw "$Stage 失败，退出码：$exitCode"
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
      $runtime.agent.guestChat -eq $true
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
      throw "8088 正由非本启动器管理的进程占用；为保护其他进程，拒绝关闭。"
    }
    Write-Host "本地服务当前未运行。" -ForegroundColor Yellow
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
  Write-Host "AI 知识导航已关闭。" -ForegroundColor Green
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
    throw "拒绝处理非项目虚拟环境路径。"
  }

  if (Test-Path -LiteralPath $venvRoot) {
    Write-Host "检测到损坏的项目虚拟环境，正在安全重建..." -ForegroundColor Yellow
    Remove-Item -LiteralPath $venvRoot -Recurse -Force
  }

  $script:stage = "重建虚拟环境"
  $createArguments = @($basePython.PrefixArguments) + @("-m", "venv", $venvRoot)
  Invoke-CheckedProcess $script:stage $basePython.FilePath $createArguments
  if (-not (Test-PythonCommand $venvPython)) {
    throw "新虚拟环境无法启动。"
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
    Write-Host "依赖未变化，跳过安装。" -ForegroundColor DarkGray
    return
  }

  $script:stage = "安装依赖"
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
    throw "无法读取新服务进程信息。"
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
  $state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
}

function Start-ManagedService {
  if (Test-ManagedProcess) {
    if (Test-ExistingAiNav) {
      Write-Host "AI 知识导航已经在运行：http://127.0.0.1:8088/" -ForegroundColor Green
      return
    }
    Write-Host "检测到失去健康状态的受管服务，正在重新部署..." -ForegroundColor Yellow
    Stop-ManagedService
  } elseif (Test-LocalPortOccupied) {
    throw "端口 8088 已被非本启动器管理的服务占用；未停止或覆盖该进程。"
  }

  $script:stage = "检查虚拟环境"
  $venvRebuilt = Ensure-VirtualEnvironment
  Ensure-Dependencies -ForceInstall $venvRebuilt

  foreach ($logPath in ($stdoutPath, $stderrPath)) {
    if (Test-Path -LiteralPath $logPath) {
      Remove-Item -LiteralPath $logPath -Force
    }
  }

  $script:stage = "启动应用"
  Write-Host "正在部署 AI 知识导航：http://127.0.0.1:8088/" -ForegroundColor Cyan
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
    throw "应用未在 30 秒内就绪。日志：$stderrPath"
  }
  Write-Host "部署完成：http://127.0.0.1:8088/" -ForegroundColor Green
  Write-Host "日志目录：$launcherRoot" -ForegroundColor DarkGray
}

function Show-ControlMenu {
  while ($true) {
    Write-Host ""
    if ((Test-ManagedProcess) -and (Test-ExistingAiNav)) {
      Write-Host "状态：运行中  http://127.0.0.1:8088/" -ForegroundColor Green
    } elseif (Test-LocalPortOccupied) {
      Write-Host "状态：8088 被非本启动器管理的进程占用" -ForegroundColor Red
    } else {
      Write-Host "状态：已关闭" -ForegroundColor Yellow
    }

    $choice = Read-Host "[R] 重新部署  [S] 关闭服务  [Q] 退出控制窗口  [Enter] 刷新状态"
    switch ($choice.Trim().ToUpperInvariant()) {
      "R" {
        if (Test-ManagedProcess) {
          Stop-ManagedService
        } elseif (Test-LocalPortOccupied) {
          Write-Host "拒绝重启：8088 不属于本启动器。" -ForegroundColor Red
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
        Write-Host "控制窗口已退出；服务保持当前状态。" -ForegroundColor DarkGray
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
    $script:stage = "关闭应用"
    Stop-ManagedService
    return
  }

  if ($Restart) {
    $script:stage = "重新部署"
    if (Test-ManagedProcess) {
      Stop-ManagedService
    } elseif (Test-LocalPortOccupied) {
      throw "端口 8088 不属于本启动器，拒绝重新部署。"
    }
  }

  Start-ManagedService
  if ($NoPause) {
    return
  }
  Show-ControlMenu
  return
} catch {
  Write-Host "一键部署失败（阶段：$script:stage）" -ForegroundColor Red
  Write-Host $_.Exception.Message -ForegroundColor Red
  Write-Host "日志目录：$launcherRoot" -ForegroundColor DarkGray
  if (-not $NoPause) {
    Read-Host "按 Enter 关闭窗口"
  }
  exit 1
}
