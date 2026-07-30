from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HttpStaticRevalidationTest(unittest.TestCase):
    def test_prefixed_project_responses_revalidate_after_a_release_switch(self) -> None:
        config = (ROOT / "deploy" / "http-test" / "nginx" / "ai-nav.conf").read_text(
            encoding="utf-8"
        )
        start = config.index("location /StarChart-AI/ {")
        end = config.index("\n    }", start)
        project_location = config[start:end]
        self.assertIn('add_header Cache-Control "no-cache" always;', project_location)

    def test_only_fingerprinted_brand_asset_is_immutable(self) -> None:
        config = (ROOT / "deploy" / "http-test" / "nginx" / "ai-nav.conf").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            config,
            r"location = /StarChart-AI/assets/img/brand-mark\.[a-f0-9]{8}\.svg",
        )
        self.assertEqual(config.count("max-age=31536000, immutable"), 1)
        self.assertIn("gzip_types text/css application/javascript application/json image/svg+xml;", config)


if __name__ == "__main__":
    unittest.main()
