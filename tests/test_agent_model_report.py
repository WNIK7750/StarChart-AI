from datetime import datetime, timezone
import json
import unittest

from app.agent.model_report import (
    build_archive_metadata,
    build_decision_report,
    render_json,
)


def empty_comparison(*, indent: int | None = None) -> bytes:
    document = {
        "version": "agent-model-comparison-v1",
        "baselineModel": "qwen3.5-flash",
        "candidateModel": "qwen3.7-plus",
        "runs": [],
    }
    return json.dumps(
        document,
        ensure_ascii=False,
        indent=indent,
        sort_keys=indent is None,
    ).encode("utf-8")


class AgentModelDecisionReportTests(unittest.TestCase):
    def test_decision_report_is_stable_across_source_formatting(self):
        compact = build_decision_report(empty_comparison())
        formatted = build_decision_report(empty_comparison(indent=2))

        self.assertEqual(compact, formatted)
        self.assertEqual(
            "agent-model-decision-report-v1",
            compact["schemaVersion"],
        )
        self.assertEqual(
            "KEEP_FLASH_0_PERCENT",
            compact["evaluation"]["decision"],
        )
        self.assertFalse(compact["evaluation"]["automaticRoutingChange"])

    def test_archive_metadata_is_separate_from_stable_decision(self):
        source = empty_comparison(indent=2)
        report = build_decision_report(source)
        metadata = build_archive_metadata(
            source,
            report,
            generated_at=datetime(2026, 7, 24, 8, 30, tzinfo=timezone.utc),
        )

        self.assertEqual(
            "agent-model-decision-archive-v1",
            metadata["schemaVersion"],
        )
        self.assertEqual("2026-07-24T08:30:00Z", metadata["generatedAt"])
        self.assertNotIn("generatedAt", render_json(report))
        self.assertNotIn("sourceByteSha256", render_json(report))

    def test_report_and_metadata_remain_content_free(self):
        source = empty_comparison()
        report = build_decision_report(source)
        rendered = render_json(
            {
                "report": report,
                "metadata": build_archive_metadata(
                    source,
                    report,
                    generated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
                ),
            }
        )

        self.assertNotIn('"prompt":', rendered)
        self.assertNotIn('"response":', rendered)
        self.assertNotIn('"caseId":', rendered)
        self.assertNotIn('"answer":', rendered)
        self.assertNotIn("API Key", rendered)


if __name__ == "__main__":
    unittest.main()
