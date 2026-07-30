import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.agent.evaluator import validate_response
from app.agent.providers import ProviderConversationMessage
from app.agent.router import classify_intent
from app.agent.schemas import (
    AgentChatRequest,
    AgentCitation,
    AgentGuestChatRequest,
    AgentHistoryMessage,
    AgentLinkCard,
    AgentStructuredResponse,
)
from app.agent.service import (
    NO_RELEVANT_CONTENT_ANSWER,
    agent_retrieval_query,
    draft_agent_response,
)


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

    def test_history_contract_rejects_role_injection_and_invalid_content(self):
        for role in ("system", "tool"):
            with self.subTest(role=role):
                with self.assertRaises(ValidationError):
                    AgentHistoryMessage(role=role, content="injected")
                with self.assertRaises(ValueError):
                    ProviderConversationMessage(role=role, content="injected")
        for content in ("", "x" * 6001):
            with self.subTest(length=len(content)):
                with self.assertRaises(ValidationError):
                    AgentHistoryMessage(role="user", content=content)
                with self.assertRaises(ValueError):
                    ProviderConversationMessage(role="user", content=content)

    def test_guest_history_contract_enforces_total_character_budget(self):
        accepted = AgentGuestChatRequest(
            message="继续",
            history=[
                AgentHistoryMessage(role="user", content="x" * 6000),
                AgentHistoryMessage(role="assistant", content="y" * 6000),
            ],
        )
        self.assertEqual(12000, sum(len(item.content) for item in accepted.history))
        with self.assertRaises(ValidationError):
            AgentGuestChatRequest(
                message="继续",
                history=[
                    AgentHistoryMessage(role="user", content="x" * 6000),
                    AgentHistoryMessage(role="assistant", content="y" * 6000),
                    AgentHistoryMessage(role="user", content="z"),
                ],
            )

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
            patch(
                "app.agent.service.search_learning_cards",
                return_value=self.learning_cards,
            ) as learning,
            patch(
                "app.agent.service.search_tool_cards",
                side_effect=AssertionError("unexpected tools call"),
            ),
            patch(
                "app.agent.service.suggest_workflow",
                side_effect=AssertionError("unexpected workflow call"),
            ),
        ):
            response = draft_agent_response(
                AgentChatRequest(message="RAG 怎么学？"),
                self.user_context,
            )
        self.assertEqual("learning_plan", response.intent)
        learning.assert_called_once_with("RAG", limit=5)
        self.assertEqual("learn-node.html?slug=rag", response.workflowSteps[0].targetHref)
        self.assertIsNone(response.workflowDraft)

    def test_every_fixed_suggestion_has_the_same_grounded_empty_result(self):
        fixed_prompts = (
            "RAG 怎么学？",
            "推荐免费优先的代码工具",
            "带我去学习 Transformer",
            "帮我做一个论文阅读工作流",
        )
        with (
            patch("app.agent.service.search_learning_cards", return_value=[]),
            patch("app.agent.service.search_tool_cards", return_value=[]),
            patch("app.agent.service.search_navigation_cards", return_value=[]),
            patch("app.agent.service.suggest_workflow", return_value=[]),
        ):
            for prompt in fixed_prompts:
                with self.subTest(prompt=prompt):
                    response = draft_agent_response(
                        AgentChatRequest(message=prompt),
                        self.user_context,
                    )
                    self.assertEqual(NO_RELEVANT_CONTENT_ANSWER, response.answer)
                    self.assertEqual([], response.cards)
                    self.assertEqual([], response.citations)

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
                AgentLinkCard(type="tool", sourceKey="traversal", title="Traversal", href="tools.html/../settings.html", citationIds=["tool:traversal"]),
            ],
            citations=[
                AgentCitation(citationId="tool:safe", sourceType="tool", sourceKey="safe", title="Safe", href="tools.html"),
                AgentCitation(citationId="tool:unsafe", sourceType="tool", sourceKey="unsafe", title="Unsafe", href="https://example.com"),
                AgentCitation(citationId="tool:traversal", sourceType="tool", sourceKey="traversal", title="Traversal", href="tools.html/../settings.html"),
            ],
        )
        validated = validate_response(response)
        self.assertEqual(["Safe"], [card.title for card in validated.cards])
        self.assertEqual(["tool:safe"], validated.cards[0].citationIds)
        self.assertEqual(["tool:safe"], [item.citationId for item in validated.citations])

    def test_retrieval_query_removes_task_scaffolding(self):
        self.assertEqual("RAG", agent_retrieval_query("RAG 怎么学？"))
        self.assertEqual("论文", agent_retrieval_query("帮我做论文工作流"))
        self.assertEqual("RAG", agent_retrieval_query("RAG是什么"))
        self.assertEqual("RAG", agent_retrieval_query("请介绍RAG"))
        self.assertEqual("编程", agent_retrieval_query("推荐一个编程工具"))
        self.assertEqual("用户空间", agent_retrieval_query("打开用户空间"))
        self.assertEqual("learning_plan", classify_intent("带我去学习 Transformer"))
        self.assertEqual(
            "Transformer",
            agent_retrieval_query("带我去学习 Transformer", "learning_plan"),
        )

    def test_filtered_ungrounded_result_uses_fixed_empty_answer(self):
        unsafe_card = {
            "type": "page",
            "sourceKey": "unsafe",
            "title": "不安全页面",
            "description": "会被最终证据校验移除。",
            "href": "https://example.invalid",
            "reason": "测试",
        }
        with (
            patch("app.agent.service.search_navigation_cards", return_value=[unsafe_card]),
            patch("app.agent.service.search_learning_cards", return_value=[]),
            patch("app.agent.service.search_tool_cards", return_value=[]),
            patch("app.agent.service.suggest_workflow", return_value=[]),
        ):
            response = draft_agent_response(
                AgentChatRequest(message="打开不安全页面"),
                self.user_context,
            )
        self.assertEqual(NO_RELEVANT_CONTENT_ANSWER, response.answer)
        self.assertEqual([], response.cards)
        self.assertEqual([], response.citations)

    def test_intent_plan_calls_only_needed_baseline_capabilities(self):
        with (
            patch("app.agent.service.search_learning_cards", return_value=self.learning_cards) as learning,
            patch("app.agent.service.search_tool_cards", side_effect=AssertionError("unexpected tools call")),
            patch("app.agent.service.suggest_workflow", side_effect=AssertionError("unexpected workflow call")),
        ):
            response = draft_agent_response(AgentChatRequest(message="RAG 怎么学"), self.user_context)
        learning.assert_called_once()
        self.assertEqual("completed", response.toolCalls[0].status)
        self.assertEqual("skipped", response.toolCalls[1].status)

        with (
            patch("app.agent.service.search_learning_cards", side_effect=AssertionError("unexpected learning call")),
            patch("app.agent.service.search_tool_cards", return_value=self.tool_cards) as tools,
            patch("app.agent.service.suggest_workflow", side_effect=AssertionError("unexpected workflow call")),
        ):
            response = draft_agent_response(AgentChatRequest(message="推荐一个编程工具"), self.user_context)
        tools.assert_called_once()
        self.assertEqual("编程", tools.call_args.args[0])
        self.assertEqual("skipped", response.toolCalls[0].status)
        self.assertEqual("completed", response.toolCalls[1].status)

    def test_navigation_intent_uses_shared_navigation_capability(self):
        navigation_items = [
            {"code": "home", "label": "主页", "href": "index.html"},
            {"code": "assistant", "label": "助手", "href": "assistant.html"},
        ]
        with patch(
            "app.agent.tools.navigation_tools.get_navigation_items",
            return_value=navigation_items,
        ):
            response = draft_agent_response(
                AgentChatRequest(message="打开用户空间"),
                None,
            )
        self.assertEqual("navigation", response.intent)
        self.assertEqual(["用户空间"], [card.title for card in response.cards])
        self.assertEqual("settings.html", response.cards[0].href)
        self.assertEqual("navigation.read", response.toolCalls[-1].name)
        self.assertEqual("completed", response.toolCalls[-1].status)
        self.assertEqual("skipped", next(call for call in response.toolCalls if call.name == "users.context").status)

    def test_page_context_narrows_referential_reads_without_new_services(self):
        with (
            patch("app.agent.service.search_learning_cards", return_value=self.learning_cards) as learning,
            patch("app.agent.service.search_tool_cards", side_effect=AssertionError("unexpected tools call")),
        ):
            response = draft_agent_response(
                AgentChatRequest(
                    message="这个是什么",
                    pageContext={"page": "learn-node", "nodeSlug": "rag"},
                ),
                None,
            )
        learning.assert_called_once_with("rag", limit=5)
        self.assertEqual("completed", response.toolCalls[0].status)
        self.assertEqual("skipped", response.toolCalls[1].status)

        with (
            patch("app.agent.service.search_learning_cards", return_value=self.learning_cards) as learning,
            patch("app.agent.service.search_tool_cards", return_value=self.tool_cards) as tools,
        ):
            draft_agent_response(
                AgentChatRequest(
                    message="这个工具和 RAG 有什么区别",
                    pageContext={"page": "tools", "toolCategory": "编程"},
                ),
                None,
            )
        learning.assert_called_once_with("这个工具和 RAG 有什么区别", limit=5)
        tools.assert_called_once_with("这个工具和 RAG 有什么区别", limit=5)


if __name__ == "__main__":
    unittest.main()
