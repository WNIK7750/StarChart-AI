import inspect
import json
import unittest
from unittest.mock import patch

import httpx

from app.agent.runtime import get_agent_runtime_profile
from app.agent.schemas import AgentCapabilities
from app.core.config import (
    AgentProviderSettings,
    validate_agent_provider_config,
)


def provider_config(**overrides) -> dict:
    values = {
        "environment": "test",
        "provider": "deterministic",
        "base_url": "",
        "model": "qwen3.5-flash",
        "api_key": "",
        "timeout_seconds": 8,
        "max_retries": 1,
        "max_output_tokens": 600,
        "max_output_chars": 6000,
        "max_evidence_items": 10,
        "max_evidence_chars": 12000,
    }
    values.update(overrides)
    return values


class AgentFeatureMatrixTests(unittest.IsolatedAsyncioTestCase):
    def test_live_switch_is_rejected_for_non_live_provider_modes(self):
        for provider in ("deterministic", "fake"):
            with self.subTest(provider=provider), self.assertRaisesRegex(
                RuntimeError,
                "requires.*openai_compatible",
            ):
                validate_agent_provider_config(
                    **provider_config(
                        provider=provider,
                        live_enabled=True,
                    )
                )

    def test_runtime_profile_distinguishes_safe_provider_modes(self):
        cases = (
            (
                AgentProviderSettings(
                    provider="deterministic",
                    base_url="",
                    model="qwen3.5-flash",
                    api_key="",
                ),
                "deterministic",
                False,
            ),
            (
                AgentProviderSettings(
                    provider="fake",
                    base_url="",
                    model="fake-model",
                    api_key="",
                ),
                "fake",
                False,
            ),
            (
                AgentProviderSettings(
                    provider="openai_compatible",
                    base_url="https://private-provider.example/v1",
                    model="qwen3.5-flash",
                    api_key="private-secret",
                    live_enabled=False,
                ),
                "configured_off",
                False,
            ),
            (
                AgentProviderSettings(
                    provider="openai_compatible",
                    base_url="https://private-provider.example/v1",
                    model="qwen3.5-flash",
                    api_key="private-secret",
                    live_enabled=True,
                ),
                "live",
                True,
            ),
        )
        for settings, expected_mode, expected_live in cases:
            with self.subTest(mode=expected_mode), patch(
                "app.agent.runtime.get_agent_provider_settings",
                return_value=settings,
            ):
                profile = get_agent_runtime_profile()
            self.assertEqual(expected_mode, profile.provider.mode)
            self.assertEqual(expected_live, profile.provider.live)
            self.assertFalse(profile.safety.automaticRequestRetry)
            self.assertFalse(profile.safety.upgradeRoutingEnabled)
            rendered = json.dumps(profile.model_dump(), ensure_ascii=False)
            self.assertNotIn("private-secret", rendered)
            self.assertNotIn("private-provider.example", rendered)
            self.assertNotIn("apiKey", rendered)
            self.assertNotIn("baseUrl", rendered)

    def test_invalid_provider_configuration_has_safe_snapshot(self):
        with patch(
            "app.agent.runtime.get_agent_provider_settings",
            side_effect=RuntimeError("sensitive internal configuration detail"),
        ):
            profile = get_agent_runtime_profile()

        self.assertEqual("invalid", profile.provider.mode)
        self.assertFalse(profile.provider.configurationValid)
        self.assertIsNone(profile.provider.model)
        self.assertNotIn(
            "sensitive internal configuration detail",
            json.dumps(profile.model_dump()),
        )

    def test_public_capabilities_contract_remains_minimal(self):
        capabilities = AgentCapabilities(stream=True, sessions=True)
        self.assertEqual(
            {"stream": True, "sessions": True, "transportVersion": 1},
            capabilities.model_dump(),
        )

    async def test_runtime_http_contract_requires_users_manage(self):
        from app.main import app, iter_app_routes

        route = next(
            route
            for route in iter_app_routes()
            if getattr(route, "path", None) == "/api/v1/agent/operations/runtime"
        )
        auth_dependency = route.dependant.dependencies[0].call
        self.assertEqual(
            "users:manage",
            inspect.getclosurevars(auth_dependency).nonlocals["permission"],
        )
        previous_overrides = dict(app.dependency_overrides)
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                unauthorized = await client.get("/api/v1/agent/operations/runtime")
                self.assertEqual(401, unauthorized.status_code)

                app.dependency_overrides[auth_dependency] = lambda: {
                    "id": 1,
                    "permissions": ["users:manage"],
                }
                authorized = await client.get("/api/v1/agent/operations/runtime")
                self.assertEqual(200, authorized.status_code)
                body = authorized.json()
                self.assertFalse(body["meta"]["containsSecrets"])
                self.assertFalse(body["meta"]["containsProviderEndpoint"])
                self.assertNotIn("apiKey", json.dumps(body))
                self.assertNotIn("baseUrl", json.dumps(body))
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)


if __name__ == "__main__":
    unittest.main()
