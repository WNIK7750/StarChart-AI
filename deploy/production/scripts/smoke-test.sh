#!/usr/bin/env bash
set -euo pipefail

base_url="${1:-https://starchart-ai.xyz}"

check_ok() {
  curl --fail --silent --show-error --max-time 15 "$1" >/dev/null
}

check_ok http://127.0.0.1:8003/api/v1/health
check_ok "${base_url}/"
check_ok "${base_url}/assistant"
check_ok "${base_url}/learn"
check_ok "${base_url}/learn/rag"
check_ok "${base_url}/tools"
check_ok "${base_url}/settings"
check_ok "${base_url}/api/v1/runtime/public"

headers="$(mktemp)"
trap 'rm -f "${headers}"' EXIT
curl --fail --silent --show-error --max-time 15 \
  --dump-header "${headers}" --output /dev/null "${base_url}/"
for expected in \
  "strict-transport-security:" \
  "content-security-policy:" \
  "x-content-type-options: nosniff"; do
  if ! grep --fixed-strings --ignore-case --quiet "${expected}" "${headers}"; then
    echo "Missing security header: ${expected}" >&2
    exit 1
  fi
done

www_status="$(
  curl --silent --show-error --max-time 15 --output /dev/null \
    --write-out '%{http_code} %{redirect_url}' \
    https://www.starchart-ai.xyz/
)"
if [[ "${www_status}" != "308 https://starchart-ai.xyz/" ]]; then
  echo "Unexpected www redirect: ${www_status}" >&2
  exit 1
fi

echo "Production HTTPS smoke checks passed."
