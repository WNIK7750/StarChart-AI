#!/usr/bin/env bash
set -euo pipefail

failed=0

check_path() {
  local path="$1"
  if [[ ! -e "${path}" ]]; then
    echo "MISSING ${path}" >&2
    failed=1
  fi
}

check_mode() {
  local path="$1"
  local mode
  mode="$(stat -c '%a' "${path}" 2>/dev/null || true)"
  if [[ "${mode}" != "640" && "${mode}" != "600" ]]; then
    echo "UNSAFE_MODE ${path}" >&2
    failed=1
  fi
}

for endpoint in 127.0.0.1:8000 127.0.0.1:8001 127.0.0.1:8002; do
  port="${endpoint##*:}"
  ss -ltnH "sport = :${port}" || failed=1
done

for directory in \
  /srv/starchart-ai-http-test/data \
  /srv/starchart-ai-http-test/uploads \
  /srv/starchart-ai-provider-preview/data \
  /srv/starchart-ai-provider-preview/uploads; do
  check_path "${directory}"
  test -w "${directory}" || failed=1
done

public_env=/etc/starchart-ai/http-test.env
preview_env=/etc/starchart-ai/provider-preview.env
check_path "${public_env}"
check_path "${preview_env}"
if [[ -e "${public_env}" ]]; then check_mode "${public_env}"; fi
if [[ -e "${preview_env}" ]]; then check_mode "${preview_env}"; fi

public_database=/srv/starchart-ai-http-test/data/ai_nav.sqlite3
preview_database=/srv/starchart-ai-provider-preview/data/ai_nav.sqlite3
if [[ "${public_database}" == "${preview_database}" ]]; then
  echo "DATABASE_PATHS_NOT_ISOLATED" >&2
  failed=1
fi

nginx -t || failed=1
exit "${failed}"
