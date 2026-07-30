from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.platform import frontend_routes


def make_client() -> TestClient:
    application = FastAPI()
    application.include_router(frontend_routes.router)
    return TestClient(application)


class FrontendRoutesTest(unittest.TestCase):
    def test_canonical_pages_serve_existing_html(self) -> None:
        client = make_client()
        for path in ("/", "/assistant", "/learn", "/learn/rag", "/tools", "/settings"):
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(200, response.status_code)
                self.assertIn("text/html", response.headers["content-type"])

    def test_legacy_pages_redirect_to_prefixed_clean_routes(self) -> None:
        client = make_client()
        expected = {
            "/index.html": "/StarChart-AI/",
            "/assistant.html": "/StarChart-AI/assistant",
            "/learn.html": "/StarChart-AI/learn",
            "/learn-node.html?slug=rag": "/StarChart-AI/learn/rag",
            "/tools.html?q=RAG": "/StarChart-AI/tools?q=RAG",
            "/settings.html?workflow=wf_1": "/StarChart-AI/settings?workflow=wf_1",
        }
        with patch.object(frontend_routes, "PUBLIC_BASE_PATH", "/StarChart-AI"):
            for legacy, location in expected.items():
                with self.subTest(legacy=legacy):
                    response = client.get(legacy, follow_redirects=False)
                    self.assertEqual(308, response.status_code)
                    self.assertEqual(location, response.headers["location"])

    def test_learning_legacy_route_moves_slug_into_path_and_preserves_other_query(self) -> None:
        client = make_client()
        response = client.get(
            "/learn-node.html?slug=rag&source=search&source=history",
            follow_redirects=False,
        )
        self.assertEqual(308, response.status_code)
        self.assertEqual(
            "/learn/rag?source=search&source=history",
            response.headers["location"],
        )
        missing = client.get("/learn-node.html?source=search", follow_redirects=False)
        self.assertEqual(308, missing.status_code)
        self.assertEqual("/learn?source=search", missing.headers["location"])

    def test_invalid_learning_slugs_and_trailing_slashes_are_canonicalized(self) -> None:
        client = make_client()
        self.assertEqual(404, client.get("/learn/Bad_Slug").status_code)
        response = client.get("/assistant/", follow_redirects=False)
        self.assertEqual(308, response.status_code)
        self.assertEqual("/assistant", response.headers["location"])


if __name__ == "__main__":
    unittest.main()
