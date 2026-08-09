#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

overlay_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
identity="starchart-ai-production"

if ! getent group "${identity}" >/dev/null; then
  groupadd --system "${identity}"
fi
if ! id -u "${identity}" >/dev/null 2>&1; then
  useradd --system --gid "${identity}" --home-dir /nonexistent \
    --shell /usr/sbin/nologin "${identity}"
fi

install -d -o "${identity}" -g "${identity}" -m 0700 \
  /srv/starchart-ai-production/data \
  /srv/starchart-ai-production/uploads
install -d -o root -g root -m 0700 /var/backups/starchart-ai-production
install -d -o root -g root -m 0751 /etc/starchart-ai
install -d -o root -g root -m 0755 /var/www/letsencrypt
install -m 0644 \
  "${overlay_root}/systemd/starchart-ai-production.service" \
  /etc/systemd/system/starchart-ai-production.service

if [[ ! -e /etc/starchart-ai/production.env ]]; then
  install -m 0640 -o root -g "${identity}" \
    "${overlay_root}/env.example" \
    /etc/starchart-ai/production.env
fi
chown root:"${identity}" /etc/starchart-ai/production.env
chmod 0640 /etc/starchart-ai/production.env
systemctl daemon-reload

echo "Production staging files installed."
echo "No service was started, no DNS was changed, and no certificate was requested."
echo "Fill /etc/starchart-ai/production.env interactively before starting the service."
