param(
  [switch]$NoPause
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$venvRoot = Join-Path $root ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$stage = "初始化"

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
      -not [string]::IsNullOrWhiteSpace([string]$runtime.deploymentProfile)
    )
  } catch {
    return $false
  }
}

function Test-LocalPortOccupied {
  $client = [Net.Sockets.TcpClient]::new()
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

try {
  $stage = "解析 Python"
  $basePython = Resolve-BasePython

  $stage = "检查虚拟环境"
  if (-not (Test-PythonCommand $venvPython)) {
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

    $stage = "重建虚拟环境"
    $createArguments = @($basePython.PrefixArguments) + @("-m", "venv", $venvRoot)
    Invoke-CheckedProcess $stage $basePython.FilePath $createArguments
    if (-not (Test-PythonCommand $venvPython)) {
      throw "新虚拟环境无法启动。"
    }
  }

  $stage = "安装依赖"
  Invoke-CheckedProcess $stage $venvPython @(
    "-m",
    "pip",
    "install",
    "-r",
    (Join-Path $root "backend\requirements.txt")
  )

  $stage = "检查本地服务"
  if (Test-ExistingAiNav) {
    Write-Host "AI 知识导航已经在运行：http://127.0.0.1:8088/" -ForegroundColor Green
    if (-not $NoPause) {
      Read-Host "按 Enter 关闭窗口"
    }
    exit 0
  }

  if (Test-LocalPortOccupied) {
    throw "端口 8088 已被其他服务占用；未停止或覆盖该进程。"
  }

  $stage = "启动应用"
  Write-Host "正在启动 AI 知识导航：http://127.0.0.1:8088/" -ForegroundColor Cyan
  Invoke-CheckedProcess $stage $venvPython @("backend\run.py")
  exit 0
} catch {
  Write-Host "一键启动失败（阶段：$stage）" -ForegroundColor Red
  Write-Host $_.Exception.Message -ForegroundColor Red
  if (-not $NoPause) {
    Read-Host "按 Enter 关闭窗口"
  }
  exit 1
}
