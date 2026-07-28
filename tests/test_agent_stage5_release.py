import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "04-operations" / "agent" / "agent-stage5-release-runbook.md"
AUDIT = ROOT / "docs" / "06-evidence" / "agent" / "agent_stage5_experience_audit.json"
COMPLETION_AUDIT = (
    ROOT / "docs" / "06-evidence" / "agent" / "agent_development_completion_audit.json"
)
TASKS = ROOT / "docs" / "03-domains" / "agent" / "agent-development-tasks.md"
HANDOFF = ROOT / "docs" / "03-domains" / "agent" / "agent-development-handoff.md"
PROVIDER_ADR = ROOT / "docs" / "02-architecture" / "decisions" / "adr-agent-provider-cn.md"
PROVIDER_RELEASE = (
    ROOT / "docs" / "04-operations" / "agent" / "agent-provider-stage1-release-checklist.md"
)
LEARNING_PLAN = ROOT / "docs" / "03-domains" / "learning" / "learning-area-foundation-plan.md"
PROJECT_ROADMAP = ROOT / "docs" / "01-overview" / "project-wide-optimization-roadmap.md"


class AgentStage5ReleaseTests(unittest.TestCase):
    def test_runbook_covers_required_release_and_rollback_contract(self):
        text = RUNBOOK.read_text(encoding="utf-8")
        for heading in (
            "## 功能开关",
            "## 已知限制",
            "## Provider 数据边界",
            "## 并发与成本阈值",
            "## 发布前门禁",
            "## 监控与告警",
            "## 回滚与故障演练",
            "## 当前可复现证据",
        ):
            self.assertIn(heading, text)
        for contract in (
            "AI_NAV_AGENT_PROVIDER=deterministic",
            "AI_NAV_AGENT_PROVIDER_LIVE_ENABLED=0",
            "AI_NAV_AGENT_PROVIDER_UPGRADE_RATIO=0",
            "AI_NAV_AGENT_PER_USER_CONCURRENCY",
            "AI_NAV_AGENT_GLOBAL_MONTHLY_COST_CNY",
            "scripts/verify-agent.ps1",
            "scripts/verify-foundation.ps1",
            "agent-provider-stage1-release-checklist.md",
        ):
            self.assertIn(contract, text)

    def test_experience_audit_is_content_free_and_tracks_pending_acceptance(self):
        audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        self.assertEqual("agent-stage5-experience-audit-v1", audit["schemaVersion"])
        self.assertEqual("complete_offline", audit["status"])
        self.assertEqual(
            ["chromium", "firefox", "webkit", "opera"],
            audit["frontend"]["browsersPassed"],
        )
        self.assertEqual(
            ["Pixel 7", "iPhone 15"],
            audit["frontend"]["deviceEmulationPassed"],
        )
        self.assertNotIn("firefox_redesign_revalidation", audit["frontend"]["pending"])
        self.assertNotIn(
            "opera_visual_and_interaction_revalidation",
            audit["frontend"]["pending"],
        )
        self.assertIn(
            "native Opera screenshot at desktop viewport",
            audit["frontend"]["conversationLayoutRedesign"]["operaConnectorChecks"],
        )
        self.assertIn(
            "connector exposes navigation content tree and screenshot but not click or console APIs",
            audit["frontend"]["conversationLayoutRedesign"]["operaConnectorLimitations"],
        )
        self.assertNotIn("real_mobile_device", audit["frontend"]["pending"])
        self.assertEqual(
            "passed_manual",
            audit["frontend"]["realDeviceAcceptance"]["status"],
        )
        self.assertFalse(
            audit["frontend"]["realDeviceAcceptance"]["containsDeviceIdentifier"],
        )
        self.assertEqual(
            "passed",
            audit["frontend"]["isolatedAcceptanceServer"]["status"],
        )
        self.assertNotIn("screen_reader_release_acceptance", audit["frontend"]["pending"])
        self.assertEqual(
            "passed_manual",
            audit["frontend"]["screenReaderAcceptance"]["status"],
        )
        self.assertEqual(
            "passed_automated",
            audit["frontend"]["conversationLayoutRedesign"]["status"],
        )
        self.assertFalse(audit["containsUserContent"])
        self.assertFalse(audit["containsCredentials"])

    def test_development_is_complete_and_only_production_tasks_remain(self):
        audit = json.loads(COMPLETION_AUDIT.read_text(encoding="utf-8"))
        self.assertEqual(
            "agent-development-completion-audit-v1",
            audit["schemaVersion"],
        )
        self.assertEqual(
            "development_complete_production_pending",
            audit["status"],
        )
        self.assertEqual([], audit["unmarkedOfflineTasks"])
        self.assertTrue(audit["offlineDevelopment"]["agentGatePassed"])
        self.assertTrue(audit["offlineDevelopment"]["foundationGatePassed"])
        self.assertTrue(audit["remainingTasks"])
        self.assertTrue(
            all(
                item["class"] == "production_release"
                and item["requiresExternalState"]
                for item in audit["remainingTasks"]
            )
        )
        self.assertFalse(audit["containsUserContent"])
        self.assertFalse(audit["containsCredentials"])

        unchecked = [
            line.strip()
            for line in TASKS.read_text(encoding="utf-8").splitlines()
            if "[ ]" in line
        ]
        self.assertTrue(unchecked)
        self.assertTrue(
            all("【上线前处理】" in line for line in unchecked),
            unchecked,
        )

        for plan in (LEARNING_PLAN, PROJECT_ROADMAP):
            self.assertNotIn("[ ]", plan.read_text(encoding="utf-8"))
        adr_unchecked = [
            line.strip()
            for line in PROVIDER_ADR.read_text(encoding="utf-8").splitlines()
            if "[ ]" in line
        ]
        self.assertTrue(adr_unchecked)
        self.assertTrue(
            all(
                "【上线前处理】" in line or "【上线后评测】" in line
                for line in adr_unchecked
            ),
            adr_unchecked,
        )
        self.assertIn("[ ]", PROVIDER_RELEASE.read_text(encoding="utf-8"))

        handoff_head = "\n".join(
            HANDOFF.read_text(encoding="utf-8").splitlines()[:130]
        )
        self.assertIn("上线前仍需完成", handoff_head)
        self.assertIn("不属于当前欠账", handoff_head)
        self.assertNotIn("尚未完成：", handoff_head)


if __name__ == "__main__":
    unittest.main()
