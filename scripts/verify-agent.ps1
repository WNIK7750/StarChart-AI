$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
. (Join-Path $PSScriptRoot "python-runtime.ps1")
$python = Resolve-AiNavPython -Root $root

function Invoke-Step {
  param([string]$Name, [scriptblock]$Command)
  Write-Host "==> $Name"
  & $Command
  if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}

Invoke-Step "Compile Agent module" {
  & $python -m py_compile `
    backend/app/agent/schemas.py `
    backend/app/agent/router.py `
    backend/app/agent/service.py `
    backend/app/agent/evaluator.py `
    backend/app/agent/evaluation_manifest.py `
    backend/app/agent/evaluation_protocol.py `
    backend/app/agent/orchestrator.py `
    backend/app/agent/observability.py `
    backend/app/agent/replay.py `
    backend/app/agent/runtime.py `
    backend/app/agent/sessions.py `
    backend/app/agent/streaming.py `
    backend/app/agent/governance.py `
    backend/app/agent/model_gate.py `
    backend/app/agent/model_report.py `
    backend/app/agent/factory.py `
    backend/app/agent/providers/base.py `
    tests/support/fake_provider.py `
    backend/app/agent/providers/openai_compatible.py `
    backend/app/agent/tools/learning_tools.py `
    backend/app/agent/tools/catalog_tools.py `
    backend/app/agent/tools/navigation_tools.py `
    backend/app/platform/navigation.py `
    backend/run.py `
    scripts/benchmark-agent-runtime.py `
    scripts/evaluate-agent-model-upgrade.py `
    scripts/build-agent-evaluation-manifest.py `
    scripts/build-agent-blind-protocol-manifest.py `
    scripts/compile-agent-blind-evaluation.py `
    scripts/rehearse-agent-stage2.py `
    scripts/serve-agent-stage5-acceptance.py `
    backend/app/core/config.py `
    backend/app/api/v1/routers/agent.py `
    tests/test_agent_eval_cases.py `
    tests/test_agent_observability.py `
    tests/test_agent_services.py `
    tests/test_agent_provider.py `
    tests/test_agent_replay.py `
    tests/test_agent_runtime.py `
    tests/test_agent_sessions.py
}

Invoke-Step "Agent service tests" {
  & $python -m unittest discover -s tests -p "test_agent*.py" -v
}

Invoke-Step "Agent evaluation manifest" {
  & $python scripts/build-agent-evaluation-manifest.py --check
}

Invoke-Step "Agent blind evaluation protocol manifest" {
  & $python scripts/build-agent-blind-protocol-manifest.py --check
}

Invoke-Step "Agent model decision baseline" {
  & $python scripts/evaluate-agent-model-upgrade.py `
    --input docs/04-operations/agent/agent-model-comparison-template.json `
    --output docs/06-evidence/agent/agent_model_comparison_empty_report.json `
    --check
}

Invoke-Step "Agent frontend contract" {
  node --test tests/test_agent_frontend.mjs tests/test_agent_sse.mjs
}

Invoke-Step "Agent frontend syntax" {
  node --check frontend/assets/js/assistant-page.js
}

Invoke-Step "Whitespace check" {
  git diff --check
}
