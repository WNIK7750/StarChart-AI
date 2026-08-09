#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

overlay_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
active_site="/etc/nginx/sites-available/starchart-ai-production"
enabled_site="/etc/nginx/sites-enabled/starchart-ai-production"
backup_root="/var/backups/starchart-ai-production/nginx-$(date -u +%Y%m%dT%H%M%SZ)-acme"
had_active=0
had_enabled=0

install -d -o root -g root -m 0700 "${backup_root}"
install -d -o root -g root -m 0755 /var/www/letsencrypt
if [[ -e "${active_site}" ]]; then
  had_active=1
  cp --archive "${active_site}" "${backup_root}/starchart-ai-production"
fi
if [[ -e "${enabled_site}" || -L "${enabled_site}" ]]; then
  had_enabled=1
fi
install -m 0644 "${overlay_root}/nginx/starchart-ai-acme.conf" "${active_site}"
ln -sfn "${active_site}" "${enabled_site}"

if nginx -t; then
  systemctl reload nginx
else
  if [[ "${had_active}" -eq 1 ]]; then
    cp --archive "${backup_root}/starchart-ai-production" "${active_site}"
  else
    rm -f "${active_site}"
  fi
  if [[ "${had_enabled}" -eq 0 ]]; then
    rm -f "${enabled_site}"
  fi
  echo "Nginx validation failed; the previous site state was restored." >&2
  exit 1
fi

echo "ACME-only virtual host installed. The production application remains unavailable."
