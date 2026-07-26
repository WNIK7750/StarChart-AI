#!/usr/bin/env bash
set -euo pipefail

failed=0
phase="${1:-before-first-start}"

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

check_listener_present() {
  local endpoint="$1"
  local port="${endpoint##*:}"
  local rows
  if ! rows="$(ss -ltnH "sport = :${port}")"; then
    echo "LISTENER_CHECK_FAILED ${endpoint}" >&2
    failed=1
  elif [[ -z "${rows}" ]]; then
    echo "LEGACY_LISTENER_MISSING ${endpoint}" >&2
    failed=1
  fi
}

check_listener_absent() {
  local endpoint="$1"
  local port="${endpoint##*:}"
  local rows
  if ! rows="$(ss -ltnH "sport = :${port}")"; then
    echo "LISTENER_CHECK_FAILED ${endpoint}" >&2
    failed=1
  elif [[ -n "${rows}" ]]; then
    echo "NEW_LISTENER_ALREADY_PRESENT ${endpoint}" >&2
    failed=1
  fi
}

case "${phase}" in
  before-first-start)
    # Legacy is serving; neither new instance has started.
    check_listener_present 127.0.0.1:8000
    check_listener_absent 127.0.0.1:8001
    check_listener_absent 127.0.0.1:8002
    ;;
  before-provider-preview)
    # Legacy and public test are serving; preview has not started.
    check_listener_present 127.0.0.1:8000
    check_listener_present 127.0.0.1:8001
    check_listener_absent 127.0.0.1:8002
    ;;
  *)
    echo "UNSUPPORTED_PREFLIGHT_PHASE ${phase}" >&2
    exit 2
    ;;
esac

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
