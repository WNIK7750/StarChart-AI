#!/usr/bin/env bash
set -euo pipefail

curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1:8001/api/v1/health >/dev/null
curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1/StarChart-AI/ >/dev/null
curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1/StarChart-AI/api/v1/runtime/public >/dev/null

echo "Local deterministic HTTP smoke checks passed."
