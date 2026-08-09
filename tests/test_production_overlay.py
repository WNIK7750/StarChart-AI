from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "deploy" / "production"


def read_overlay(relative_path: str) -> str:
    return (OVERLAY / relative_path).read_text(encoding="utf-8")


def assignments(relative_path: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in read_overlay(relative_path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        result[name] = value
    return result


class ProductionEnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = assignments("env.example")

    def test_template_is_https_root_domain_and_fail_closed_for_secrets(self) -> None:
        self.assertEqual("production", self.env["AI_NAV_ENV"])
        self.assertEqual("", self.env["AI_NAV_PUBLIC_BASE_PATH"])
        self.assertEqual("https://starchart-ai.xyz", self.env["AI_NAV_CORS_ALLOW_ORIGINS"])
        self.assertEqual("1", self.env["AI_NAV_REFRESH_COOKIE_SECURE"])
        self.assertEqual("1", self.env["AI_NAV_HTTPS_CONFIRMED"])
        for name in (
            "AI_NAV_SECRET_KEY",
        ):
            self.assertEqual("", self.env[name], name)

    def test_template_has_no_site_default_model_key_or_cost_budget(self) -> None:
        self.assertEqual("1", self.env["AI_NAV_API_WORKERS"])
        self.assertEqual("process_local", self.env["AI_NAV_AGENT_RUNTIME_STATE_BACKEND"])
        self.assertEqual("deterministic", self.env["AI_NAV_AGENT_PROVIDER"])
        self.assertEqual("0", self.env["AI_NAV_AGENT_PROVIDER_LIVE_ENABLED"])
        self.assertEqual("1", self.env["AI_NAV_AGENT_STREAM_ENABLED"])
        self.assertEqual("1", self.env["AI_NAV_AGENT_SESSIONS_ENABLED"])
        self.assertEqual("unconfigured", self.env["AI_NAV_AGENT_CREDENTIAL_STORE"])
        self.assertIn("dashscope.aliyuncs.com", self.env["AI_NAV_AGENT_USER_MODEL_ALLOWED_HOSTS"])
        for removed_name in (
            "AI_NAV_AGENT_PROVIDER_API_KEY",
            "AI_NAV_AGENT_PROVIDER_MODEL",
            "AI_NAV_AGENT_PER_REQUEST_COST_CNY",
            "AI_NAV_AGENT_GLOBAL_MONTHLY_COST_CNY",
        ):
            self.assertNotIn(removed_name, self.env)

    def test_only_example_environment_files_are_tracked(self) -> None:
        environment_files = [
            path.relative_to(OVERLAY).as_posix()
            for path in OVERLAY.rglob("*")
            if path.is_file()
            and (path.name == ".env" or path.name == "env.example" or ".env." in path.name)
        ]
        self.assertEqual(["env.example"], environment_files)


class ProductionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unit = read_overlay("systemd/starchart-ai-production.service")

    def test_service_is_loopback_only_single_worker_and_data_isolated(self) -> None:
        for expected in (
            "User=starchart-ai-production",
            "Group=starchart-ai-production",
            "EnvironmentFile=/etc/starchart-ai/production.env",
            "Environment=AI_NAV_APP_HOST=127.0.0.1",
            "Environment=AI_NAV_APP_PORT=8003",
            "Environment=AI_NAV_API_WORKERS=1",
            "Environment=AI_NAV_DATABASE_PATH=/srv/starchart-ai-production/data/ai_nav.sqlite3",
            "Environment=AI_NAV_UPLOAD_DIR=/srv/starchart-ai-production/uploads",
            "ReadWritePaths=/srv/starchart-ai-production",
            "NoNewPrivileges=true",
            "ProtectSystem=strict",
            "ProtectHome=true",
            "WantedBy=multi-user.target",
        ):
            self.assertIn(expected, self.unit)
        self.assertNotIn("User=root", self.unit)
        self.assertNotIn("/srv/starchart-ai-http-test/data", self.unit)
        self.assertNotIn("/srv/starchart-ai-provider-preview/data", self.unit)


class ProductionNginxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = read_overlay("nginx/starchart-ai.conf")

    def test_domain_redirects_to_one_https_canonical_origin(self) -> None:
        self.assertIn("server_name starchart-ai.xyz www.starchart-ai.xyz;", self.config)
        self.assertIn("server_name www.starchart-ai.xyz;", self.config)
        self.assertIn("server_name starchart-ai.xyz;", self.config)
        self.assertGreaterEqual(
            self.config.count("return 308 https://starchart-ai.xyz$request_uri;"),
            2,
        )
        self.assertNotIn("/StarChart-AI", self.config)

    def test_tls_proxy_and_streaming_boundaries_are_explicit(self) -> None:
        for expected in (
            "127.0.0.1:8003",
            "ssl_protocols TLSv1.2 TLSv1.3;",
            "Strict-Transport-Security",
            "proxy_set_header X-Forwarded-Proto https;",
            "location = /api/v1/agent/chat/stream",
            "proxy_buffering off;",
            "proxy_read_timeout 300s;",
            "client_max_body_size 3m;",
        ):
            self.assertIn(expected, self.config)
        upstream_endpoints = re.findall(r"\bserver\s+(127\.0\.0\.1:\d+);", self.config)
        self.assertEqual(["127.0.0.1:8003"], upstream_endpoints)

    def test_auth_and_agent_have_independent_rate_limits(self) -> None:
        self.assertIn("zone=starchart_prod_auth:10m rate=10r/m", self.config)
        self.assertIn("zone=starchart_prod_agent:10m rate=20r/m", self.config)
        self.assertIn("limit_req zone=starchart_prod_auth", self.config)
        self.assertIn("limit_req zone=starchart_prod_agent", self.config)

    def test_acme_config_exposes_only_the_challenge_path(self) -> None:
        config = read_overlay("nginx/starchart-ai-acme.conf")
        self.assertIn("server_name starchart-ai.xyz www.starchart-ai.xyz;", config)
        self.assertIn("location ^~ /.well-known/acme-challenge/", config)
        self.assertIn("root /var/www/letsencrypt;", config)
        self.assertIn("return 503;", config)
        self.assertNotIn("proxy_pass", config)


class ProductionScriptTests(unittest.TestCase):
    def test_staging_installer_never_starts_services_or_touches_dns(self) -> None:
        script = read_overlay("scripts/install-staging.sh")
        self.assertIn("/srv/starchart-ai-production/data", script)
        self.assertIn("/etc/starchart-ai/production.env", script)
        self.assertIn("systemctl daemon-reload", script)
        self.assertNotRegex(script, r"systemctl\s+(?:start|restart|enable|reload)\b")
        self.assertNotRegex(script, r"\b(certbot|acme\.sh|dig|nsupdate)\b")

    def test_https_installer_is_certificate_and_nginx_test_gated(self) -> None:
        script = read_overlay("scripts/install-https.sh")
        certificate_check = script.index("MISSING_CERTIFICATE")
        install_site = script.index('install -m 0644 "${overlay_root}/nginx/starchart-ai.conf"')
        nginx_test = script.index("nginx -t")
        nginx_reload = script.index("systemctl reload nginx")
        self.assertLess(certificate_check, install_site)
        self.assertLess(install_site, nginx_test)
        self.assertLess(nginx_test, nginx_reload)
        self.assertIn("the previous site state was restored", script)
        self.assertIn('rm -f "${enabled_site}"', script)

    def test_acme_installer_tests_nginx_before_reload_without_starting_app(self) -> None:
        script = read_overlay("scripts/install-acme.sh")
        install_site = script.index(
            'install -m 0644 "${overlay_root}/nginx/starchart-ai-acme.conf"'
        )
        nginx_test = script.index("nginx -t")
        nginx_reload = script.index("systemctl reload nginx")
        self.assertLess(install_site, nginx_test)
        self.assertLess(nginx_test, nginx_reload)
        self.assertNotRegex(script, r"systemctl\s+(?:start|restart|enable)\b")
        self.assertNotIn("certbot certonly", script)
        self.assertIn("the previous site state was restored", script)
        self.assertIn('rm -f "${enabled_site}"', script)

    def test_preflight_is_read_only_and_requires_loopback_production(self) -> None:
        script = read_overlay("scripts/preflight.sh")
        for expected in (
            "before-staging",
            "before-acme",
            "before-https",
            "check_listener 8001 present",
            "check_listener 8003 absent",
            "check_listener 8003 present",
            "MISSING_COMMAND",
            "/etc/letsencrypt/live/starchart-ai.xyz/fullchain.pem",
            "/etc/starchart-ai/production.env",
            "nginx -t",
        ):
            self.assertIn(expected, script)
        self.assertNotRegex(
            script,
            r"\b(rm|mv|cp|install|mkdir|chmod|chown|systemctl\s+(?:start|stop|restart|reload))\b",
        )

    def test_backup_and_restore_are_explicit_and_never_replace_production(self) -> None:
        backup = read_overlay("scripts/backup.sh")
        restore = read_overlay("scripts/restore-rehearsal.sh")
        self.assertIn("manage-users-backup.py", backup)
        self.assertIn("/var/backups/starchart-ai-production", backup)
        self.assertIn("/srv/starchart-ai-production/rehearsal/restore.sqlite3", restore)
        self.assertNotIn("--replace", restore)


if __name__ == "__main__":
    unittest.main()
