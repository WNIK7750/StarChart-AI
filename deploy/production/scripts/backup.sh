#!/usr/bin/env bash
set -euo pipefail

release_root="${1:-/opt/starchart-ai/current}"
database="/srv/starchart-ai-production/data/ai_nav.sqlite3"
backup_root="/var/backups/starchart-ai-production"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="${backup_root}/ai_nav-${timestamp}.sqlite3"

install -d -o root -g root -m 0700 "${backup_root}"
"/opt/starchart-ai/venv/bin/python" \
  "${release_root}/scripts/manage-users-backup.py" \
  backup --source "${database}" --output "${output}"
chmod 0600 "${output}"
echo "Production database backup verified: ${output}"
