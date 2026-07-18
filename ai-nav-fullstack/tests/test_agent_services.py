import unittest
from unittest.mock import patch

from app.agent.evaluator import validate_response
from app.agent.schemas import AgentChatRequest, AgentCitation, AgentLinkCard, AgentStructuredResponse
from app.agent.service import agent_retrieval_query, draft_agent_response


class AgentServicesTest(unittest.TestCase):
    def setUp(self):
        self.user_context = {
            "preferences": {"freeFirst": True, "cnFirst": False},
            "assets": {"activeCount": 2, "recent": []},
            "capabilities": {"agentChat": True, "saveWorkflow": True},
            "meta": {"source": "users.context", "contractVersion": 1},
        }
        self.learning_cards = [{
            "type": "learning_node",
            "sourceKey": "rag",
            "title": "RAG",
            "description": "检索增强生成学习节点。",
            "href": "learn-node.html?slug=rag",
            "reason": "站内学习节点",
        }]
        self.tool_cards = [{
            "type": "tool",
            "sourceKey": "chatgpt",
            "title": "ChatGPT",
            "description": "通用 AI 工具。",
            "href": "tools.html?q=ChatGPT#directory",
            "reason": "名称匹配",
            "tags": ["免费"],
            "isFree": True,
        }]

    def test_response_contract_combines_read_only_domain_contexts(self):
        with (
            patch("app.agent.service.search_learning_cards", return_value=self.learning_cards),
            patch("app.agent.service.search_tool_cards", return_value=self.tool_cards),
            patch("app.agent.service.suggest_workflow", return_value=[]),
        ):
            response = draft_agent_response(AgentChatRequest(message="RAG 是什么"), self.user_context)
        self.assertEqual("qa", response.intent)
        self.assertEqual(["RAG", "ChatGPT"], [card.title for card in response.cards])
        self.assertEqual(["learning_node:rag", "tool:chatgpt"], [item.citationId for item in response.citations])
        self.assertEqual(
            ["learning.search", "tools.search", "tools.workflow", "users.context"],
            [call.name for call in response.toolCalls],
        )
        self.assertTrue(response.meta.readOnly)
        self.assertEqual("users.context", response.meta.userContext.source)

    def test_learning_plan_is_deterministic_and_not_persisted(self):
        with (
            patch("app.agent.service.search_learning_cards", return_value=self.learning_cards),
            patch("app.agent.service.search_tool_cards", return_value=[]),
        ):
            response = draft_agent_response(AgentChatRequest(message="RAG 怎么学"), self.user_context)
        self.assertEqual("learning_plan", response.intent)
        self.assertEqual("learn-node.html?slug=rag", response.workflowSteps[0].targetHref)
        self.assertIsNone(response.workflowDraft)

    def test_workflow_draft_uses_tools_and_requires_separate_save_command(self):
        workflow = [{
            "code": "paper-reading",
            "title": "论文阅读工作流",
            "description": "阅读与整理。",
            "tools": [{"id": "chatgpt", "name": "ChatGPT", "href": "tools.html?q=ChatGPT#directory", "officialUrl": "https://chatgpt.com"}],
        }]
        with (
            patch("app.agent.service.search_learning_cards", return_value=[]),
            patch("app.agent.service.search_tool_cards", return_value=self.tool_cards),
            patch("app.agent.service.suggest_workflow", return_value=workflow),
        ):
            response = draft_agent_response(AgentChatRequest(message="帮我做论文工作流"), self.user_context)
        self.assertEqual("workflow_generation", response.intent)
        self.assertEqual("paper-reading", response.workflowDraft.sourceRef)
        self.assertEqual("tool:chatgpt", response.workflowSteps[0].citationIds[0])
        self.assertTrue(response.meta.readOnly)

    def test_response_guard_removes_external_links_and_dangling_citations(self):
        response = AgentStructuredResponse(
            answer="test",
            cards=[
                AgentLinkCard(type="tool", sourceKey="safe", title="Safe", href="tools.html", citationIds=["tool:safe", "tool:unsafe"]),
                AgentLinkCard(type="tool", sourceKey="unsafe", title="Unsafe", href="https://example.com", citationIds=["tool:unsafe"]),
            ],
            citations=[
                AgentCitation(citationId="tool:safe", sourceType="tool", sourceKey="safe", title="Safe", href="tools.html"),
                AgentCitation(citationId="tool:unsafe", sourceType="tool", sourceKey="unsafe", title="Unsafe", href="https://example.com"),
            ],
        )
        validated = validate_response(response)
        self.assertEqual(["Safe"], [card.title for card in validated.cards])
        self.assertEqual(["tool:safe"], validated.cards[0].citationIds)
        self.assertEqual(["tool:safe"], [item.citationId for item in validated.citations])

    def test_retrieval_query_removes_task_scaffolding(self):
        self.assertEqual("RAG", agent_retrieval_query("RAG 怎么学？"))
        self.assertEqual("论文", agent_retrieval_query("帮我做论文工作流"))


if __name__ == "__main__":
    unittest.main()
