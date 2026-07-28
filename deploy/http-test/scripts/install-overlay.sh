#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

overlay_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backup_root="/var/backups/starchart-ai/nginx-$(date -u +%Y%m%dT%H%M%SZ)"
active_site="/etc/nginx/sites-available/ai-nav"

ensure_service_identity() {
  local identity="$1"
  if ! getent group "${identity}" >/dev/null; then
    groupadd --system "${identity}"
  fi
  if ! id -u "${identity}" >/dev/null 2>&1; then
    useradd --system --gid "${identity}" --home-dir /nonexistent \
      --shell /usr/sbin/nologin "${identity}"
  fi
}

ensure_service_identity starchart-ai-http-test
ensure_service_identity starchart-ai-provider-preview

mkdir -p "${backup_root}"
if [[ -e "${active_site}" ]]; then
  cp --archive "${active_site}" "${backup_root}/ai-nav"
fi

install -d -o starchart-ai-http-test -g starchart-ai-http-test -m 0700 \
  /srv/starchart-ai-http-test/data \
  /srv/starchart-ai-http-test/uploads
install -d -o starchart-ai-provider-preview -g starchart-ai-provider-preview -m 0700 \
  /srv/starchart-ai-provider-preview/data \
  /srv/starchart-ai-provider-preview/uploads
install -d -o root -g root -m 0751 /etc/starchart-ai
install -d -o root -g root -m 0755 /var/www/project-hub/assets
install -m 0644 "${overlay_root}/project-hub/index.html" /var/www/project-hub/index.html
install -m 0644 "${overlay_root}/project-hub/assets/styles.css" /var/www/project-hub/assets/styles.css
install -m 0644 "${overlay_root}/nginx/ai-nav.conf" "${active_site}"
install -m 0644 "${overlay_root}/systemd/starchart-ai-http-test.service" /etc/systemd/system/
install -m 0644 "${overlay_root}/systemd/starchart-ai-provider-preview.service" /etc/systemd/system/

if [[ ! -e /etc/starchart-ai/http-test.env ]]; then
  install -m 0640 -o root -g starchart-ai-http-test "${overlay_root}/env.example" /etc/starchart-ai/http-test.env
fi
if [[ ! -e /etc/starchart-ai/provider-preview.env ]]; then
  install -m 0640 -o root -g starchart-ai-provider-preview \
    "${overlay_root}/provider-preview.env.example" \
    /etc/starchart-ai/provider-preview.env
fi
chown root:starchart-ai-http-test /etc/starchart-ai/http-test.env
chmod 0640 /etc/starchart-ai/http-test.env
chown root:starchart-ai-provider-preview /etc/starchart-ai/provider-preview.env
chmod 0640 /etc/starchart-ai/provider-preview.env

ln -sfn "${active_site}" /etc/nginx/sites-enabled/ai-nav
systemctl daemon-reload

if nginx -t; then
  systemctl reload nginx
else
  echo "Nginx syntax validation failed; nginx was not reloaded." >&2
  echo "Restore the previous configuration from ${backup_root} before retrying." >&2
  exit 1
fi

echo "Templates installed. No credentials were generated."
echo "Edit each /etc/starchart-ai/*.env file interactively and keep its dedicated group and mode 0640."
echo "Provision each isolated database separately, then start only the public service."
echo "The Provider preview service is manual and loopback-only."
