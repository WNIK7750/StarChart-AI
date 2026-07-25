import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import BaseModel
from python_multipart import MultipartParser
from python_multipart.exceptions import MultipartParseError
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

from app.main import app, iter_app_routes


class InputSecurityRegressionTest(unittest.TestCase):
    def test_security_headers_cover_html_api_errors_and_static_assets(self):
        client = TestClient(app)
        for path in ("/", "/api/v1/health/live", "/api/v1/not-a-real-route", "/assets/js/api.js"):
            response = client.get(path)
            self.assertEqual("nosniff", response.headers["X-Content-Type-Options"])
            self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])
            self.assertNotIn("unsafe-eval", response.headers["Content-Security-Policy"])
            self.assertEqual("DENY", response.headers["X-Frame-Options"])
            self.assertEqual("strict-origin-when-cross-origin", response.headers["Referrer-Policy"])
            self.assertIn("camera=()", response.headers["Permissions-Policy"])
            self.assertNotIn("Strict-Transport-Security", response.headers)

    def test_all_json_business_operations_define_a_success_response_schema(self):
        schema = app.openapi()
        missing = []
        operations = 0
        json_operations = 0
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if method not in {"get", "post", "put", "patch", "delete"}:
                    continue
                operations += 1
                responses = operation.get("responses", {})
                success = next(
                    (responses[code] for code in ("200", "201", "202", "204") if code in responses),
                    {},
                )
                json_media = success.get("content", {}).get("application/json")
                if json_media is None:
                    continue
                json_operations += 1
                if not json_media.get("schema"):
                    missing.append(f"{method.upper()} {path}")
        self.assertEqual([], missing)
        self.assertEqual(88, operations)
        self.assertEqual(84, json_operations)

    def test_all_json_response_models_are_field_level_allowlists(self):
        response_models = [
            route.response_model
            for route in iter_app_routes()
            if getattr(route, "response_model", None) is not None
        ]
        self.assertEqual(84, len(response_models))
        self.assertTrue(
            all(
                isinstance(model, type)
                and issubclass(model, BaseModel)
                and model.model_config.get("extra") in {"forbid", "ignore"}
                for model in response_models
            )
        )

    def test_nested_internal_response_fields_are_filtered_before_serialization(self):
        with patch(
            "app.api.v1.routers.common.get_navigation_items",
            return_value=[
                {
                    "code": "home",
                    "label": "主页",
                    "href": "index.html",
                    "internalSecret": "must-not-leak",
                }
            ],
        ):
            response = TestClient(app).get("/api/v1/navigation")
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            [{"code": "home", "label": "主页", "href": "index.html"}],
            response.json()["items"],
        )
        self.assertNotIn("must-not-leak", response.text)

    def test_avatar_request_is_rejected_before_multipart_parsing_when_too_large(self):
        response = TestClient(app).post(
            "/api/v1/users/me/avatar",
            content=b"",
            headers={"Content-Type": "multipart/form-data; boundary=x", "Content-Length": "99999999"},
        )
        self.assertEqual(413, response.status_code)
        self.assertEqual("AVATAR_REQUEST_TOO_LARGE", response.json()["detail"]["code"])

    def test_multipart_header_count_and_total_body_are_bounded(self):
        parser = MultipartParser(b"x", max_size=128 * 1024, max_header_count=8, max_header_size=4224)
        excessive_headers = (
            b"--x\r\n"
            + b"".join(f"X-{index}: value\r\n".encode() for index in range(9))
            + b"\r\npayload\r\n--x--\r\n"
        )
        with self.assertRaises(MultipartParseError):
            parser.write(excessive_headers)

        parser = MultipartParser(b"x", max_size=128 * 1024)
        bounded_preamble_and_epilogue = (
            b"p" * (64 * 1024)
            + b"\r\n--x\r\nContent-Disposition: form-data; name=\"file\"\r\n\r\nok\r\n--x--\r\n"
            + b"e" * (64 * 1024)
        )
        started = time.perf_counter()
        with self.assertRaises(MultipartParseError):
            parser.write(bounded_preamble_and_epilogue)
        self.assertLess(time.perf_counter() - started, 1.0)

    def test_static_files_many_ranges_remain_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "asset.txt").write_bytes(b"a" * 4096)
            static_app = Starlette(routes=[Mount("/", app=StaticFiles(directory=root))])
            many_ranges = "bytes=" + ",".join(f"{index}-{index}" for index in range(512))
            started = time.perf_counter()
            response = TestClient(static_app).get("/asset.txt", headers={"Range": many_ranges})
            self.assertIn(response.status_code, {200, 206, 400, 416})
            self.assertLess(time.perf_counter() - started, 1.0)


if __name__ == "__main__":
    unittest.main()
