from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "deploy" / "http-test"


def read_overlay(relative_path: str) -> str:
    return (OVERLAY / relative_path).read_text(encoding="utf-8")


def location_body(config: str, route: str, modifier: str = "") -> str:
    header = rf"location\s+{re.escape(modifier)}\s*{re.escape(route)}\s*\{{"
    match = re.search(header, config)
    if match is None:
        raise AssertionError(f"missing location {modifier} {route}".strip())
    depth = 1
    position = match.end()
    while position < len(config) and depth:
        if config[position] == "{":
            depth += 1
        elif config[position] == "}":
            depth -= 1
        position += 1
    if depth:
        raise AssertionError(f"unclosed location {route}")
    return config[match.end() : position - 1]


class HttpTestNginxOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = read_overlay("nginx/ai-nav.conf")

    def test_uses_only_named_loopback_upstreams_and_never_exposes_preview(self) -> None:
        upstreams = re.findall(
            r"upstream\s+([a-zA-Z0-9_]+)\s*\{(?P<body>.*?)\}",
            self.config,
            re.DOTALL,
        )
        self.assertEqual([name for name, _ in upstreams], ["legacy_ai_nav", "starchart_http_test"])
        self.assertIn("127.0.0.1:8000", upstreams[0][1])
        self.assertIn("127.0.0.1:8001", upstreams[1][1])
        self.assertNotIn("8002", self.config)
        self.assertTrue(
            all(
                re.fullmatch(r"127\.0\.0\.1:(?:8000|8001)", endpoint)
                for _, body in upstreams
                for endpoint in re.findall(r"\bserver\s+([^;\s]+)", body)
            )
        )

    def test_preserves_legacy_routes_before_static_fallback(self) -> None:
        chat_position = self.config.index("location = /chat")
        health_position = self.config.index("location = /health")
        widget_position = self.config.index("location = /chat-widget.js")
        fallback_position = self.config.index("location / {")
        self.assertLess(max(chat_position, health_position, widget_position), fallback_position)
        self.assertIn("proxy_pass http://legacy_ai_nav", location_body(self.config, "/chat", "="))
        self.assertIn("proxy_pass http://legacy_ai_nav", location_body(self.config, "/health", "="))
        widget = location_body(self.config, "/chat-widget.js", "=")
        self.assertIn("alias /opt/ai-nav2/chat-widget.js", widget)
        self.assertNotIn("try_files", widget)
        self.assertIn("/var/www/project-hub", location_body(self.config, "/"))

    def test_normalizes_prefixes_and_strips_new_project_prefix(self) -> None:
        self.assertRegex(
            location_body(self.config, "/StarChart-AI", "="),
            r"return\s+308\s+/StarChart-AI/;",
        )
        self.assertRegex(
            location_body(self.config, "/old-ai-nav", "="),
            r"return\s+308\s+/old-ai-nav/;",
        )
        project = location_body(self.config, "/StarChart-AI/")
        self.assertIn("proxy_pass http://starchart_http_test/", project)
        self.assertIn("proxy_set_header X-Forwarded-Prefix /StarChart-AI", project)
        self.assertIn("proxy_set_header Host $host", project)
        self.assertIn("proxy_set_header X-Forwarded-Proto $scheme", project)
        self.assertIn("proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for", project)

    def test_guest_route_has_independent_tight_limits(self) -> None:
        self.assertRegex(
            self.config,
            r"limit_req_zone\s+\$binary_remote_addr\s+zone=starchart_guest:[^;]+\s+rate=10r/m;",
        )
        guest = location_body(
            self.config,
            "/StarChart-AI/api/v1/agent/guest/chat",
            "=",
        )
        self.assertRegex(guest, r"limit_req\s+zone=starchart_guest\s+burst=5\s+nodelay;")
        self.assertRegex(guest, r"client_max_body_size\s+64k;")
        self.assertRegex(guest, r"proxy_(?:connect|read|send)_timeout\s+[0-9]+s;")
        self.assertIn("proxy_pass http://starchart_http_test/api/v1/agent/guest/chat", guest)


class HttpTestServiceOverlayTests(unittest.TestCase):
    def test_units_are_isolated_hardened_and_single_worker(self) -> None:
        public = read_overlay("systemd/starchart-ai-http-test.service")
        preview = read_overlay("systemd/starchart-ai-provider-preview.service")
        self.assertIn("User=starchart-ai-http-test", public)
        self.assertIn("Group=starchart-ai-http-test", public)
        self.assertIn("User=starchart-ai-provider-preview", preview)
        self.assertIn("Group=starchart-ai-provider-preview", preview)
        for unit in (public, preview):
            self.assertNotIn("User=root", unit)
            self.assertIn("NoNewPrivileges=true", unit)
            self.assertIn("PrivateTmp=true", unit)
            self.assertIn("ProtectSystem=strict", unit)
            self.assertIn("ProtectHome=true", unit)
            self.assertIn("UMask=0077", unit)
            self.assertRegex(unit, r"Environment=AI_NAV_API_WORKERS=1")
            self.assertIn("ReadOnlyPaths=/opt/starchart-ai", unit)
            self.assertIn("WorkingDirectory=/opt/starchart-ai/current", unit)
            self.assertIn(
                "ExecStart=/opt/starchart-ai/venv/bin/python backend/run.py",
                unit,
            )
            self.assertNotIn("/current/ai-nav-fullstack", unit)
        self.assertIn("EnvironmentFile=/etc/starchart-ai/http-test.env", public)
        self.assertIn("EnvironmentFile=/etc/starchart-ai/provider-preview.env", preview)
        self.assertIn("ReadWritePaths=/srv/starchart-ai-http-test", public)
        self.assertIn("ReadWritePaths=/srv/starchart-ai-provider-preview", preview)
        self.assertIn("InaccessiblePaths=-/srv/starchart-ai-provider-preview", public)
        self.assertIn("InaccessiblePaths=-/etc/starchart-ai/provider-preview.env", public)
        self.assertIn("InaccessiblePaths=-/srv/starchart-ai-http-test", preview)
        self.assertIn("InaccessiblePaths=-/etc/starchart-ai/http-test.env", preview)
        self.assertIn("AI_NAV_DATABASE_PATH=/srv/starchart-ai-http-test/data/ai_nav.sqlite3", public)
        self.assertIn("AI_NAV_UPLOAD_DIR=/srv/starchart-ai-http-test/uploads", public)
        self.assertIn("AI_NAV_APP_PORT=8001", public)
        self.assertIn("AI_NAV_AGENT_PROVIDER=deterministic", public)
        self.assertIn("AI_NAV_AGENT_PROVIDER_LIVE_ENABLED=0", public)
        self.assertIn(
            "AI_NAV_DATABASE_PATH=/srv/starchart-ai-provider-preview/data/ai_nav.sqlite3",
            preview,
        )
        self.assertIn("AI_NAV_UPLOAD_DIR=/srv/starchart-ai-provider-preview/uploads", preview)
        self.assertIn("AI_NAV_APP_HOST=127.0.0.1", preview)
        self.assertIn("AI_NAV_APP_PORT=8002", preview)
        self.assertNotIn("WantedBy=multi-user.target", preview)

    def test_sensitive_environment_values_are_blank_in_both_templates(self) -> None:
        sensitive_names = (
            "AI_NAV_SECRET_KEY",
            "AI_NAV_HTTP_TEST_ACCOUNT_USERNAME",
            "AI_NAV_HTTP_TEST_ACCOUNT_PASSWORD",
            "AI_NAV_AGENT_PROVIDER_API_KEY",
        )
        for template in ("env.example", "provider-preview.env.example"):
            assignments = {}
            for line in read_overlay(template).splitlines():
                if line and not line.startswith("#") and "=" in line:
                    name, value = line.split("=", 1)
                    assignments[name] = value
            for name in sensitive_names:
                if name in assignments:
                    self.assertEqual(assignments[name], "", f"{template}: {name} must be blank")
        self.assertIn(
            "AI_NAV_AGENT_PROVIDER_API_KEY=",
            read_overlay("provider-preview.env.example"),
        )

    def test_environment_files_are_example_templates_only(self) -> None:
        environment_files = [
            path.relative_to(OVERLAY).as_posix()
            for path in OVERLAY.rglob("*")
            if path.is_file()
            and (path.name == ".env" or path.name == "env.example" or ".env." in path.name)
        ]
        self.assertCountEqual(
            environment_files,
            ["env.example", "provider-preview.env.example"],
        )
        self.assertTrue(
            all(
                Path(name).name == "env.example"
                or Path(name).name.endswith(".env.example")
                for name in environment_files
            )
        )

    def test_environment_templates_use_the_implemented_process_local_backend(
        self,
    ) -> None:
        for template in ("env.example", "provider-preview.env.example"):
            self.assertIn(
                "AI_NAV_AGENT_RUNTIME_STATE_BACKEND=process_local",
                read_overlay(template),
            )
            self.assertNotIn(
                "AI_NAV_AGENT_RUNTIME_STATE_BACKEND=memory",
                read_overlay(template),
            )

    def test_environment_templates_enable_authenticated_agent_sessions(
        self,
    ) -> None:
        for template in ("env.example", "provider-preview.env.example"):
            self.assertIn(
                "AI_NAV_AGENT_SESSIONS_ENABLED=1",
                read_overlay(template),
            )


class HttpTestScriptAndHubTests(unittest.TestCase):
    def test_install_is_backup_first_and_reload_is_gated_by_nginx_test(self) -> None:
        script = read_overlay("scripts/install-overlay.sh")
        backup_position = script.index("cp --archive")
        install_position = script.index("install -m 0644")
        syntax_position = script.index("nginx -t")
        reload_position = script.index("systemctl reload nginx")
        self.assertLess(backup_position, install_position)
        self.assertLess(syntax_position, reload_position)
        self.assertRegex(
            script,
            re.compile(r"if\s+nginx -t; then.*systemctl reload nginx", re.DOTALL),
        )
        self.assertNotRegex(script, r"(openssl|uuidgen|random|SECRET_KEY=.*[^=])")

    def test_preflight_is_read_only_and_checks_required_boundaries(self) -> None:
        script = read_overlay("scripts/preflight.sh")
        for expected in (
            "127.0.0.1:8000",
            "127.0.0.1:8001",
            "127.0.0.1:8002",
            "/srv/starchart-ai-http-test",
            "/srv/starchart-ai-provider-preview",
            "/etc/starchart-ai/http-test.env",
            "/etc/starchart-ai/provider-preview.env",
            "nginx -t",
        ):
            self.assertIn(expected, script)
        self.assertNotRegex(script, r"\b(rm|mv|cp|install|mkdir|chmod|chown|systemctl\s+(?:start|stop|restart|reload))\b")
        self.assertIn('phase="${1:-before-first-start}"', script)
        self.assertIn("LEGACY_LISTENER_MISSING ${endpoint}", script)
        self.assertIn("NEW_LISTENER_ALREADY_PRESENT ${endpoint}", script)
        self.assertIn("check_listener_present 127.0.0.1:8000", script)
        self.assertIn("check_listener_absent 127.0.0.1:8001", script)
        self.assertIn("check_listener_absent 127.0.0.1:8002", script)
        self.assertIn("before-provider-preview)", script)
        self.assertRegex(
            script,
            r"(?s)before-provider-preview\).*check_listener_present 127\.0\.0\.1:8001"
            r".*check_listener_absent 127\.0\.0\.1:8002",
        )
        self.assertRegex(script, r'if\s+\[\[\s+-n\s+"\$\{rows\}"\s+\]\]')

    def test_installer_creates_distinct_service_identities_and_private_files(self) -> None:
        script = read_overlay("scripts/install-overlay.sh")
        self.assertIn("starchart-ai-http-test", script)
        self.assertIn("starchart-ai-provider-preview", script)
        self.assertRegex(
            script,
            r"install -d -o starchart-ai-http-test -g starchart-ai-http-test -m 0700",
        )
        self.assertRegex(
            script,
            r"install -d -o starchart-ai-provider-preview -g starchart-ai-provider-preview -m 0700",
        )
        self.assertIn("-g starchart-ai-http-test", script)
        self.assertIn("-g starchart-ai-provider-preview", script)

    def test_smoke_only_calls_local_deterministic_public_paths(self) -> None:
        script = read_overlay("scripts/smoke-test.sh")
        self.assertIn("http://127.0.0.1:8001/api/v1/health", script)
        self.assertIn("http://127.0.0.1/StarChart-AI/", script)
        self.assertIn("http://127.0.0.1/StarChart-AI/api/v1/runtime/public", script)
        self.assertNotIn("8002", script)
        self.assertNotRegex(script, r"(register|login|provision|provider|api[_-]?key)")

    def test_hub_has_two_relative_untracked_project_links(self) -> None:
        html = read_overlay("project-hub/index.html")
        links = re.findall(r'href="([^"]+)"', html)
        self.assertIn("./old-ai-nav/", links)
        self.assertIn("./StarChart-AI/", links)
        self.assertTrue(all("://" not in link and not link.startswith("/") for link in links))
        self.assertIn("旧项目", html)
        self.assertIn("StarChart-AI", html)
        self.assertNotRegex(html, r"<script\b")
        self.assertNotRegex(html, r"(analytics|tracking|token|secret|api[_-]?key)", re.IGNORECASE)

    def test_overlay_contains_no_real_endpoint_credentials_or_windows_paths(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in OVERLAY.rglob("*")
            if path.is_file()
        )
        self.assertNotIn("47.100.94.1", combined)
        self.assertNotRegex(combined, r"[A-Za-z]:\\")
        self.assertNotRegex(combined, r"(?i)(bearer\s+[A-Za-z0-9]|cookie:\s*\S)")


if __name__ == "__main__":
    unittest.main()
