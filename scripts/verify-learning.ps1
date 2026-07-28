$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTHONIOENCODING = "utf-8"
. (Join-Path $PSScriptRoot "python-runtime.ps1")
$python = Resolve-AiNavPython -Root $root
$learningTestFiles = @(
  "test_learning_services.py",
  "test_content_governance.py",
  "test_platform_navigation.py"
)
foreach ($testFile in $learningTestFiles) {
  & $python -m unittest discover -s tests -p $testFile -v
  if ($LASTEXITCODE -ne 0) { throw "Learning unit tests failed: $testFile" }
}

$pythonFiles = Get-ChildItem backend -Recurse -Filter *.py | ForEach-Object FullName
& $python -m py_compile $pythonFiles
if ($LASTEXITCODE -ne 0) { throw "Python compilation failed." }

$skipSyntaxCheck = @("tool-data.js", "tool-page-lists.js")
Get-ChildItem frontend\assets\js -Filter *.js |
  Where-Object { $_.Name -notin $skipSyntaxCheck } |
  ForEach-Object {
    node --check $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "JavaScript syntax check failed: $($_.FullName)" }
  }

node --test tests\test_learning_frontend.mjs
if ($LASTEXITCODE -ne 0) { throw "Frontend learning tests failed." }

& $python scripts\check-learning-content.py
if ($LASTEXITCODE -ne 0) { throw "Learning content validation failed." }

& $python scripts\check-content-links.py
if ($LASTEXITCODE -ne 0) { throw "Cross-domain content link validation failed." }

& $python scripts\benchmark-learning.py --max-p95-ms 250
if ($LASTEXITCODE -ne 0) { throw "Learning performance baseline failed." }

git diff --check
if ($LASTEXITCODE -ne 0) { throw "Git whitespace validation failed." }
Write-Host "Learning verification passed." -ForegroundColor Green
