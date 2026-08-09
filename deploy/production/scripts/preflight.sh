#!/usr/bin/env bash
set -euo pipefail

phase="${1:-before-staging}"
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

check_command() {
  local name="$1"
  if ! command -v "${name}" >/dev/null 2>&1; then
    echo "MISSING_COMMAND ${name}" >&2
    failed=1
  fi
}

check_listener() {
  local port="$1"
  local expectation="$2"
  local rows
  rows="$(ss -ltnH "sport = :${port}" || true)"
  if [[ "${expectation}" == "present" && -z "${rows}" ]]; then
    echo "LISTENER_MISSING 127.0.0.1:${port}" >&2
    failed=1
  elif [[ "${expectation}" == "absent" && -n "${rows}" ]]; then
    echo "LISTENER_ALREADY_PRESENT 127.0.0.1:${port}" >&2
    failed=1
  elif [[ -n "${rows}" && "${rows}" != *"127.0.0.1:${port}"* ]]; then
    echo "LISTENER_NOT_LOOPBACK 127.0.0.1:${port}" >&2
    failed=1
  fi
}

case "${phase}" in
  before-staging)
    check_listener 8001 present
    check_listener 8003 absent
    ;;
  before-acme)
    check_listener 8001 present
    check_listener 8003 present
    check_command certbot
    ;;
  before-https)
    check_listener 8001 present
    check_listener 8003 present
    check_path /etc/letsencrypt/live/starchart-ai.xyz/fullchain.pem
    check_path /etc/letsencrypt/live/starchart-ai.xyz/privkey.pem
    ;;
  *)
    echo "UNSUPPORTED_PHASE ${phase}" >&2
    exit 2
    ;;
esac

if [[ "${phase}" != "before-staging" ]]; then
  check_path /srv/starchart-ai-production/data
  check_path /srv/starchart-ai-production/uploads
  check_path /etc/starchart-ai/production.env
  if [[ -e /etc/starchart-ai/production.env ]]; then
    check_mode /etc/starchart-ai/production.env
  fi
fi
check_command nginx
if command -v nginx >/dev/null 2>&1; then
  nginx -t || failed=1
fi
exit "${failed}"
