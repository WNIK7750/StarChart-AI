#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  echo "Usage: restore-rehearsal.sh VERIFIED_BACKUP" >&2
  exit 2
fi

release_root="/opt/starchart-ai/current"
backup="$1"
target="/srv/starchart-ai-production/rehearsal/restore.sqlite3"

install -d -o starchart-ai-production -g starchart-ai-production -m 0700 \
  /srv/starchart-ai-production/rehearsal
if [[ -e "${target}" ]]; then
  echo "Rehearsal target already exists: ${target}" >&2
  exit 1
fi
/opt/starchart-ai/venv/bin/python \
  "${release_root}/scripts/manage-users-backup.py" \
  restore --backup "${backup}" --target "${target}"
chown starchart-ai-production:starchart-ai-production "${target}"
chmod 0600 "${target}"
echo "Isolated restore rehearsal passed: ${target}"
