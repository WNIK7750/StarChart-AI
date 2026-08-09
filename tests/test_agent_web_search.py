import unittest
from types import SimpleNamespace

from app.agent.web_search import DashScopeNativeWebSearch, NativeWebSearchError
from app.agent.evaluator import validate_response
from app.agent.schemas import AgentCitation, AgentLinkCard, AgentStructuredResponse


class FakeResponses:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class DashScopeNativeWebSearchTest(unittest.TestCase):
    def test_returns_only_traceable_https_sources(self):
        response = SimpleNamespace(
            output_text="RAG 的近期实践强调检索评估与可追溯引用。",
            output=[SimpleNamespace(
                type="web_search_call",
                action=SimpleNamespace(sources=[
                    {"title": "Official guide", "url": "https://example.com/rag", "snippet": "A guide"},
                    {"title": "Unsafe", "url": "http://example.com/plain"},
                    {"title": "Local", "url": "https://localhost/admin"},
                    {"title": "Duplicate", "url": "https://example.com/rag"},
                ]),
            )],
        )
        responses = FakeResponses(response)
        search = DashScopeNativeWebSearch(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="not-a-real-key",
            model="qwen3.7-plus",
            client=SimpleNamespace(responses=responses),
        )
        results = search("RAG 最新实践", 5)
        self.assertEqual(1, len(results))
        self.assertEqual("web", results[0]["type"])
        self.assertEqual("https://example.com/rag", results[0]["href"])
        self.assertIn("检索评估", results[0]["webAnswerExcerpt"])
        self.assertEqual([{"type": "web_search"}], responses.calls[0]["tools"])

    def test_rejects_untraceable_provider_answer(self):
        response = SimpleNamespace(output_text="Untraceable", output=[])
        search = DashScopeNativeWebSearch(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="not-a-real-key",
            model="qwen3.7-plus",
            client=SimpleNamespace(responses=FakeResponses(response)),
        )
        with self.assertRaises(NativeWebSearchError):
            search("latest RAG", 3)

    def test_response_boundary_allows_only_safe_external_web_cards(self):
        response = AgentStructuredResponse(
            answer="外部来源已单独标记。",
            cards=[
                AgentLinkCard(
                    type="web", sourceKey="safe", title="Safe",
                    href="https://example.com/rag", citationIds=["web:safe"],
                ),
                AgentLinkCard(
                    type="web", sourceKey="local", title="Local",
                    href="https://localhost/admin", citationIds=["web:local"],
                ),
            ],
            citations=[
                AgentCitation(
                    citationId="web:safe", sourceType="web", sourceKey="safe",
                    title="Safe", href="https://example.com/rag",
                ),
                AgentCitation(
                    citationId="web:local", sourceType="web", sourceKey="local",
                    title="Local", href="https://localhost/admin",
                ),
            ],
        )

        validated = validate_response(response)

        self.assertEqual(["safe"], [card.sourceKey for card in validated.cards])
        self.assertEqual(["web:safe"], [item.citationId for item in validated.citations])


if __name__ == "__main__":
    unittest.main()
