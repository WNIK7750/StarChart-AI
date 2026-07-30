#!/usr/bin/env bash
set -euo pipefail

check_ok() {
  curl --fail --silent --show-error --max-time 10 "$1" >/dev/null
}

check_ok http://127.0.0.1:8001/api/v1/health
check_ok http://127.0.0.1/StarChart-AI/
check_ok http://127.0.0.1/StarChart-AI/assistant
check_ok http://127.0.0.1/StarChart-AI/learn
check_ok http://127.0.0.1/StarChart-AI/learn/rag
check_ok http://127.0.0.1/StarChart-AI/tools
check_ok http://127.0.0.1/StarChart-AI/settings
check_ok http://127.0.0.1/StarChart-AI/api/v1/runtime/public
check_ok http://127.0.0.1/StarChart-AI/assets/img/brand-mark.62793ed5.svg

legacy_headers="$(mktemp)"
trap 'rm -f "$legacy_headers"' EXIT
legacy_status="$(
  curl --silent --show-error --max-time 10 \
    --output /dev/null \
    --dump-header "$legacy_headers" \
    --write-out '%{http_code}' \
    http://127.0.0.1/StarChart-AI/assistant.html
)"
if [[ "$legacy_status" != "308" ]]; then
  echo "Legacy page route returned HTTP ${legacy_status}, expected 308." >&2
  exit 1
fi
expected_location="location: /StarChart-AI/assistant"
if ! grep --fixed-strings --ignore-case --quiet "$expected_location" "$legacy_headers"; then
  echo "Legacy page route did not redirect to the canonical assistant URL." >&2
  exit 1
fi

echo "Local deterministic HTTP smoke checks passed."
