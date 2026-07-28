Set-Location $PSScriptRoot
if (!(Test-Path ".venv")) {
  python -m venv .venv
}
.\.venv\Scripts\pip install -r backend\requirements.txt
.\.venv\Scripts\python backend\run.py
