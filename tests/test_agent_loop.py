import json
import unittest
from contextlib import asynccontextmanager
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr

from app.agent.loop import (
    AgentLoopFinalAnswer,
    SiteAgentLoopRuntime,
    _LoopInvocation,
    _ToolRecord,
)
from app.agent.orchestrator import AgentOrchestrator
from app.agent.schemas import AgentChatRequest


class ScriptedLoopModel(BaseChatModel):
    _bound_tool_names: list[str] = PrivateAttr(default_factory=list)
    _calls: int = PrivateAttr(default=0)
    _answer_payload: dict[str, Any] = PrivateAttr()

    def __init__(self, answer_payload: dict[str, Any]):
        super().__init__()
        self._answer_payload = answer_payload

    @property
    def _llm_type(self) -> str:
        return "agent-loop-test-model"

    @property
    def calls(self) -> int:
        return self._calls

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        self._bound_tool_names = [tool.name for tool in tools]
        return self

    def _generate(
        self,
        messages,
        stop=None,
        run_manager=None,
        **kwargs: Any,
    ) -> ChatResult:
        self._calls += 1
        if kwargs.get("response_format"):
            message = AIMessage(content=json.dumps(self._answer_payload, ensure_ascii=False))
        elif (
            self._bound_tool_names
            and "site_tools_search" in self._bound_tool_names
            and not any(isinstance(message, ToolMessage) for message in messages)
        ):
            message = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "site_tools_search",
                        "args": {"query": "绘图", "limit": 3},
                        "id": "search-1",
                        "type": "tool_call",
                    }
                ],
            )
        else:
            message = AIMessage(content=str(self._answer_payload.get("answer") or "已完成"))
        return ChatResult(generations=[ChatGeneration(message=message)])


class SequencedStructuredModel(ScriptedLoopModel):
    _structured_payloads: list[dict[str, Any]] = PrivateAttr(default_factory=list)
    _structured_prompts: list[str] = PrivateAttr(default_factory=list)

    def __init__(self, payloads: list[dict[str, Any]]):
        super().__init__(payloads[0])
        self._structured_payloads = list(payloads)

    def _generate(
        self,
        messages,
        stop=None,
        run_manager=None,
        **kwargs: Any,
    ) -> ChatResult:
        if kwargs.get("response_format"):
            self._calls += 1
            self._structured_prompts.append(str(messages[-1].content))
            index = min(len(self._structured_prompts) - 1, len(self._structured_payloads) - 1)
            message = AIMessage(
                content=json.dumps(self._structured_payloads[index], ensure_ascii=False)
            )
            return ChatResult(generations=[ChatGeneration(message=message)])
        return super()._generate(messages, stop, run_manager, **kwargs)


def tool_card(slug: str, title: str, description: str) -> dict[str, Any]:
    return {
        "type": "tool",
        "sourceKey": slug,
        "title": title,
        "description": description,
        "href": f"tools.html?q={title}#directory",
        "reason": "任务能力",
        "matchedCapabilities": ["visual_creation"],
        "reasonCodes": ["capability_match"],
        "tags": ["图像", "设计"],
        "isFree": False,
    }


class SiteAgentLoopRuntimeTest(unittest.TestCase):
    def test_workflow_draft_uses_model_selected_tool_evidence_in_the_same_order(self):
        records = [
            _ToolRecord(
                step_id="step-tools",
                tool_name="site_tools_search",
                title="检索站内工具",
                status="completed",
                result_count=2,
                duration_ms=1,
                payload={"_items": [
                    tool_card("elicit", "Elicit", "研究问题拆解与论文查找。"),
                    tool_card("chatpdf", "ChatPDF", "上传论文后进行问答与摘要。"),
                ]},
            ),
            _ToolRecord(
                step_id="step-workflow",
                tool_name="site_workflow_suggest",
                title="生成站内工作流候选",
                status="completed",
                result_count=1,
                duration_ms=1,
                payload={"_items": [{
                    "code": "paper-reading",
                    "title": "论文阅读工作流",
                    "description": "检索、阅读与沉淀论文。",
                    "tools": [
                        {
                            "id": "google-notebooklm",
                            "name": "Google NotebookLM",
                            "href": "tools.html?q=Google%20NotebookLM#directory",
                        },
                        {
                            "id": "perplexity",
                            "name": "Perplexity",
                            "href": "tools.html?q=Perplexity#directory",
                        },
                    ],
                }]},
            ),
        ]
        cards = SiteAgentLoopRuntime._project_cards(records)

        steps, draft = SiteAgentLoopRuntime._project_workflow(
            records,
            allow_draft=True,
            selected_source_keys=["elicit", "chatpdf"],
            cards=cards,
        )

        self.assertEqual(["Elicit", "ChatPDF"], [step.name for step in steps])
        self.assertEqual(["tool:elicit", "tool:chatpdf"], [step.citationIds[0] for step in steps])
        self.assertEqual(["elicit", "chatpdf"], [step.toolSlug for step in draft.steps])
        self.assertNotIn("Google NotebookLM", [step.name for step in steps])
        self.assertIsNone(draft.sourceRef)

    def test_workflow_candidates_are_projected_as_traceable_tool_sources(self):
        records = [_ToolRecord(
            step_id="step-workflow",
            tool_name="site_workflow_suggest",
            title="生成站内工作流候选",
            status="completed",
            result_count=1,
            duration_ms=1,
            payload={"_items": [{
                "code": "paper-reading",
                "title": "论文阅读工作流",
                "description": "检索、阅读与沉淀论文。",
                "tools": [{
                    "id": "perplexity",
                    "name": "Perplexity",
                    "description": "检索论文与背景资料。",
                    "href": "tools.html?q=Perplexity#directory",
                }],
            }]},
        )]

        cards = SiteAgentLoopRuntime._project_cards(records)
        steps, draft = SiteAgentLoopRuntime._project_workflow(
            records,
            allow_draft=True,
            selected_source_keys=["perplexity"],
            cards=cards,
        )

        self.assertEqual(["perplexity"], [card.sourceKey for card in cards])
        self.assertEqual(["Perplexity"], [step.name for step in steps])
        self.assertEqual("paper-reading", draft.sourceRef)

    def test_workflow_requires_at_least_one_selected_grounded_tool(self):
        invocation = _LoopInvocation(
            request=AgentChatRequest(message="帮我做一个论文阅读工作流"),
            history=(),
            user_context=None,
            request_id="req-workflow-grounding",
            workflow_draft_allowed=True,
            records=[_ToolRecord(
                step_id="step-workflow",
                tool_name="site_workflow_suggest",
                title="生成站内工作流候选",
                status="completed",
                result_count=1,
                duration_ms=1,
                payload={"_items": [{
                    "code": "paper-reading",
                    "title": "论文阅读工作流",
                    "tools": [{"id": "perplexity", "name": "Perplexity"}],
                }]},
            )],
        )
        ungrounded = AgentLoopFinalAnswer(
            answer="已生成论文阅读工作流。",
            intent="workflow_generation",
            objectives=[{
                "objective": "生成论文阅读工作流",
                "status": "completed",
                "explanation": "已完成。",
            }],
            selectedSourceKeys=["not-in-evidence"],
        )

        issues = SiteAgentLoopRuntime._answer_coverage_issues(invocation, ungrounded)

        self.assertTrue(any("工作流" in issue and "站内工具" in issue for issue in issues))

    def test_real_agent_loop_uses_tool_and_covers_extra_objectives(self):
        searched: list[tuple[str, int]] = []

        def search(query: str, limit: int) -> list[dict[str, Any]]:
            searched.append((query, limit))
            return [
                tool_card("gaoding-ai", "稿定 AI", "适合中文营销海报和电商排版。"),
                tool_card("chatgpt-image", "ChatGPT 图像", "适合图像生成和多轮修改。"),
                tool_card("canva-ai", "Canva AI", "适合模板排版和快速协作。"),
            ]

        model = ScriptedLoopModel(
            {
                "answer": (
                    "推荐稿定 AI、ChatGPT 图像和 Canva AI。"
                    "稿定 AI 更适合中文营销排版；ChatGPT 图像适合多轮修改；"
                    "Canva AI 适合模板协作。"
                ),
                "intent": "tool_recommendation",
                "objectives": [
                    {
                        "objective": "推荐三个绘图工具",
                        "status": "completed",
                        "explanation": "已基于站内工具事实推荐三个候选。",
                    },
                    {
                        "objective": "说明推荐原因",
                        "status": "completed",
                        "explanation": "已逐项说明适用场景。",
                    },
                ],
                "selectedSourceKeys": ["gaoding-ai", "chatgpt-image", "canva-ai"],
                "followups": [],
            }
        )
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="test",
            model_name="scripted",
            tool_search=search,
        )

        result = runtime.run(
            AgentChatRequest(message="请推荐三个绘图工具，并逐个分析说明原因"),
            request_id="req-loop-success",
        )

        self.assertEqual([("绘图", 3)], searched)
        self.assertEqual(3, model.calls)
        self.assertEqual("complete", result.response.execution.status)
        self.assertEqual("langchain_agent", result.response.meta.runtime)
        self.assertEqual(2, len(result.response.execution.objectives))
        self.assertTrue(all(item.status == "completed" for item in result.response.execution.objectives))
        self.assertEqual(3, len(result.response.cards))
        self.assertIn("适合多轮修改", result.response.answer)
        self.assertIn("run_agent", runtime.graph.get_graph().nodes)
        self.assertIn("prefetch_site_evidence", runtime.graph.get_graph().nodes)
        self.assertIn("structure_answer", runtime.graph.get_graph().nodes)
        self.assertIn("inspect", runtime.graph.get_graph().nodes)
        self.assertIn("recover_answer", runtime.graph.get_graph().nodes)
        self.assertIn("project", runtime.graph.get_graph().nodes)

    def test_selected_tool_official_domain_is_grounded_for_visible_answer(self):
        dify = tool_card("dify", "Dify", "适合搭建知识库问答。")
        dify["officialUrl"] = "https://dify.ai/"
        model = ScriptedLoopModel({
            "answer": "推荐 Dify；站内记录的官方域名是 Dify.ai，适合搭建知识库问答。",
            "intent": "tool_recommendation",
            "objectives": [{
                "objective": "推荐一个知识库工具并说明原因",
                "status": "completed",
                "explanation": "已根据站内工具事实完成。",
            }],
            "selectedSourceKeys": ["dify"],
            "followups": [],
        })
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="test",
            model_name="scripted",
            tool_search=lambda _query, _limit: [dify],
        )

        result = runtime.run(
            AgentChatRequest(message="推荐一个知识库工具并说明原因"),
            request_id="req-grounded-official-domain",
        )

        self.assertEqual("complete", result.response.execution.status)
        self.assertEqual([], result.response.execution.errors)
        self.assertIn("Dify.ai", result.response.answer)

    def test_nested_learning_resource_domain_is_removed_from_visible_answer(self):
        model = ScriptedLoopModel({
            "answer": "学习 Transformer 时可把 huggingface.co 的文档作为站内课程配套资料。",
            "intent": "learning_plan",
            "objectives": [{
                "objective": "学习 Transformer",
                "status": "completed",
                "explanation": "已基于课程资源完成。",
            }],
            "selectedSourceKeys": [],
            "followups": [],
        })
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="test",
            model_name="scripted",
            broad_prefetch=True,
            learning_search=lambda _query, _limit: [{
                "type": "learning_node",
                "sourceKey": "transformer",
                "title": "Transformer",
                "description": "学习注意力机制与模型结构。",
                "href": "learn-node.html?slug=transformer",
                "resourceHighlights": [{
                    "title": "Hugging Face Transformers 文档",
                    "href": "https://huggingface.co/docs/transformers",
                }],
            }],
            tool_search=lambda _query, _limit: [{
                **tool_card("codegeex", "CodeGeeX", "代码练习工具。"),
                "isFree": True,
            }],
        )

        result = runtime.run(
            AgentChatRequest(message="带我去学习 Transformer"),
            request_id="req-nested-resource-domain",
        )

        self.assertEqual("complete", result.response.execution.status)
        self.assertEqual([], result.response.execution.errors)
        self.assertNotIn("huggingface.co", result.response.answer)
        self.assertIn("相关资料", result.response.answer)

    def test_inline_links_are_removed_without_discarding_a_grounded_answer(self):
        cases = [
            {
                "message": "RAG 怎么学？",
                "answer": "先从 [RAG 学习内容](learn-node.html?slug=rag) 开始，理解检索、向量库与问答流程。",
                "learning": [{
                    "type": "learning_node",
                    "sourceKey": "rag",
                    "title": "RAG",
                    "description": "覆盖检索、向量库与知识库问答。",
                    "href": "learn-node.html?slug=rag",
                    "reason": "适合作为学习入口",
                }],
                "tools": [],
                "intent": "learning_plan",
            },
            {
                "message": "推荐免费优先的代码工具",
                "answer": "推荐 [CodeGeeX](tools.html?q=CodeGeeX#directory)，站内记录显示它可免费使用并适合代码补全。",
                "learning": [],
                "tools": [{
                    **tool_card("codegeex", "CodeGeeX", "支持代码补全与解释。"),
                    "isFree": True,
                }],
                "intent": "tool_recommendation",
            },
            {
                "message": "带我去学习 Transformer",
                "answer": "可以打开 [Transformer 学习内容](https://example.invalid/transformer)，先理解注意力机制再完成练习。",
                "learning": [{
                    "type": "learning_node",
                    "sourceKey": "transformer",
                    "title": "Transformer",
                    "description": "包含注意力机制、编码器与解码器。",
                    "href": "learn-node.html?slug=transformer",
                    "reason": "匹配当前学习目标",
                }],
                "tools": [],
                "intent": "learning_plan",
            },
        ]

        for index, case in enumerate(cases, start=1):
            with self.subTest(message=case["message"]):
                model = ScriptedLoopModel({
                    "answer": case["answer"],
                    "intent": case["intent"],
                    "objectives": [{
                        "objective": case["message"],
                        "status": "completed",
                        "explanation": "已根据站内证据完成。",
                    }],
                    "selectedSourceKeys": [],
                    "followups": [],
                })
                runtime = SiteAgentLoopRuntime(
                    model=model,
                    provider_name="test",
                    model_name="scripted",
                    broad_prefetch=True,
                    learning_search=lambda _query, _limit, items=case["learning"]: items,
                    tool_search=lambda _query, _limit, items=case["tools"]: items,
                )

                result = runtime.run(
                    AgentChatRequest(message=case["message"]),
                    request_id=f"req-link-recovery-{index}",
                )

                self.assertEqual("complete", result.response.execution.status)
                self.assertEqual([], result.response.execution.errors)
                self.assertNotIn("](", result.response.answer)
                self.assertNotIn("https://", result.response.answer)
                self.assertIn(
                    case["learning"][0]["title"] if case["learning"] else case["tools"][0]["title"],
                    result.response.answer,
                )
                self.assertLessEqual(model.calls, 3)

    def test_reflection_rewrites_boundary_violation_once_with_compact_notepad(self):
        invalid = {
            "answer": "先打开 [RAG 学习内容](https://outside.example/rag)，再完成一个问答练习。",
            "intent": "learning_plan",
            "objectives": [{
                "objective": "学习 RAG",
                "status": "completed",
                "explanation": "已给出学习建议。",
            }],
            "selectedSourceKeys": ["rag"],
            "followups": [],
        }
        corrected = {
            **invalid,
            "answer": "先打开下方的 RAG 学习内容，理解检索与向量库，再完成一个问答练习。",
        }
        model = SequencedStructuredModel([invalid, corrected])
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="test",
            model_name="sequenced",
            broad_prefetch=True,
            learning_search=lambda _query, _limit: [{
                "type": "learning_node",
                "sourceKey": "rag",
                "title": "RAG",
                "description": "覆盖检索、向量库与知识库问答。",
                "href": "learn-node.html?slug=rag",
                "reason": "适合作为学习入口",
            }],
            tool_search=lambda _query, _limit: [],
        )

        result = runtime.run(
            AgentChatRequest(message="RAG 怎么学？"),
            request_id="req-reflection-rewrite",
        )

        self.assertEqual("complete", result.response.execution.status)
        self.assertEqual([], result.response.execution.errors)
        self.assertIn("下方的 RAG 学习内容", result.response.answer)
        self.assertNotIn("https://", result.response.answer)
        self.assertEqual(3, model.calls)
        reflection_prompt = model._structured_prompts[-1]
        self.assertIn('"diagnosticNote"', reflection_prompt)
        self.assertIn('"category":"link"', reflection_prompt)
        self.assertNotIn("https://outside.example", reflection_prompt)
        self.assertNotIn("Traceback", reflection_prompt)
        self.assertNotIn("diagnosticNotepad", result.response.model_dump_json())

    def test_three_domain_tool_failures_handoff_to_model_without_raw_error(self):
        calls = 0

        def broken_search(_query: str, _limit: int) -> list[dict[str, Any]]:
            nonlocal calls
            calls += 1
            raise RuntimeError("database password=top-secret traceback should stay server-side")

        runtime = SiteAgentLoopRuntime(
            model=ScriptedLoopModel({}),
            provider_name="test",
            model_name="scripted",
            tool_search=broken_search,
        )
        invocation = _LoopInvocation(
            request=AgentChatRequest(message="推荐代码工具"),
            history=(),
            user_context=None,
            request_id="req-domain-handoff",
        )
        payloads = [
            json.loads(runtime._execute_search(
                invocation,
                tool_name="site_tools_search",
                title="检索站内工具",
                query=f"代码工具 {index}",
                limit=5,
                search=broken_search,
                error_code="TOOLS_SEARCH_FAILED",
            ))
            for index in range(1, 4)
        ]

        self.assertEqual(3, calls)
        self.assertTrue(payloads[0]["error"]["retryable"])
        self.assertTrue(payloads[1]["error"]["retryable"])
        self.assertFalse(payloads[2]["error"]["retryable"])
        self.assertTrue(payloads[2]["error"]["handoffToModel"])
        self.assertIn("停止继续调用工具目录", payloads[2]["instruction"])
        self.assertNotIn("password", json.dumps(payloads[2], ensure_ascii=False))
        self.assertNotIn("diagnosticId", payloads[2]["error"])
        self.assertEqual(3, len(invocation.diagnostic_notes))
        self.assertEqual("TOOLS_SEARCH_FAILED", invocation.diagnostic_notes[-1].category)
        self.assertEqual("site_tools_search", invocation.diagnostic_notes[-1].tool_name)
        self.assertGreaterEqual(len(invocation.trace), 6)

    def test_hard_output_rejection_falls_back_to_substantive_evidence_summary(self):
        model = ScriptedLoopModel({
            "answer": "<script>unsafe()</script>",
            "intent": "learning_plan",
            "objectives": [{
                "objective": "学习 RAG",
                "status": "completed",
                "explanation": "已完成。",
            }],
            "selectedSourceKeys": [],
            "followups": [],
        })
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="test",
            model_name="scripted",
            broad_prefetch=True,
            learning_search=lambda _query, _limit: [{
                "type": "learning_node",
                "sourceKey": "rag",
                "title": "RAG",
                "description": "覆盖检索、向量库与知识库问答。",
                "href": "learn-node.html?slug=rag",
                "reason": "适合作为学习入口",
            }],
            tool_search=lambda _query, _limit: [],
        )

        result = runtime.run(
            AgentChatRequest(message="RAG 怎么学？"),
            request_id="req-evidence-fallback",
        )

        self.assertEqual("partial", result.response.execution.status)
        self.assertEqual("AGENT_MODEL_REFLECTION_FAILED", result.response.execution.errors[0].code)
        self.assertIn("RAG", result.response.answer)
        self.assertIn("覆盖检索、向量库与知识库问答", result.response.answer)
        self.assertIn("建议", result.response.answer)
        self.assertNotIn("<script>", result.response.answer)
        self.assertNotIn("未通过输出校验", result.response.answer)
        self.assertLessEqual(model.calls, 3)

    def test_broad_station_retrieval_uses_original_request_before_model_filtering(self):
        tool_queries = []
        learning_queries = []
        request = "请根据站内内容为我制定 RAG 知识库问答 Demo 学习路线"
        model = ScriptedLoopModel({
            "answer": "先学习站内 RAG 节点，再使用 Canva AI 整理演示材料。",
            "intent": "learning_plan",
            "objectives": [{
                "objective": "制定 RAG 学习路线",
                "status": "completed",
                "explanation": "已基于站内检索证据完成。",
            }],
            "selectedSourceKeys": ["rag", "canva-ai"],
            "followups": [],
        })
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="test",
            model_name="scripted",
            broad_prefetch=True,
            learning_search=lambda query, _limit: (
                learning_queries.append(query) or [{
                    "type": "learning_node",
                    "sourceKey": "rag",
                    "title": "RAG",
                    "description": "包含检索、向量库与知识库问答课程。",
                    "href": "learn-node.html?slug=rag",
                    "reason": "命中 RAG、知识库、问答",
                    "outlineHighlights": [{"title": "Embedding 与向量检索", "description": "检索流程"}],
                    "resourceHighlights": [{"title": "从 0 到 1 精通 RAG", "description": "中文实战"}],
                }]
            ),
            tool_search=lambda query, _limit: (
                tool_queries.append(query) or [tool_card("canva-ai", "Canva AI", "整理演示材料。")]
            ),
        )

        result = runtime.run(AgentChatRequest(message=request), request_id="req-broad-prefetch")

        self.assertEqual(request, learning_queries[0])
        self.assertEqual(request, tool_queries[0])
        self.assertEqual(
            ["site_learning_search", "site_tools_search"],
            [step.toolName for step in result.response.execution.steps[:2]],
        )
        self.assertIn("RAG", [card.title for card in result.response.cards])
        self.assertEqual(2, model.calls)
        self.assertNotIn("site_tools_search", model._bound_tool_names)
        self.assertNotIn("site_learning_search", model._bound_tool_names)

    def test_rag_demo_route_with_code_artifact_names_reaches_visible_answer(self):
        request = (
            "请根据站内现有内容，为一个想从零学习 RAG 并做出第一个知识库问答 "
            "Demo 的用户，推荐合适的学习内容和 3 个工具，说明每项推荐理由，"
            "并给出按顺序执行的 7 天路线。"
        )
        route = "\n".join([
            "第 1 天：学习 RAG 基础。",
            "第 2 天：理解 Embedding 与向量检索。",
            "第 3 天：使用 Dify 建立知识库。",
            "第 4 天：创建 app.py，并安装 requirements.txt。",
            "第 5 天：使用 ChatDOC 检查文档问答效果。",
            "第 6 天：使用 Coze 扣子编排应用。",
            "第 7 天：补充 README.md 并完成测试。",
        ])
        model = ScriptedLoopModel({
            "answer": (
                "推荐 RAG 学习节点，因为它覆盖检索、向量库与问答流程。\n"
                "推荐 Dify、ChatDOC 和 Coze 扣子，分别用于知识库搭建、文档问答和应用编排。\n"
                f"{route}"
            ),
            "intent": "learning_plan",
            "objectives": [{
                "objective": "推荐学习内容、三个工具并给出七天路线",
                "status": "completed",
                "explanation": "已根据站内证据完成。",
            }],
            "selectedSourceKeys": ["dify", "chatdoc", "coze"],
            "followups": [],
        })
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="test",
            model_name="scripted",
            broad_prefetch=True,
            learning_search=lambda _query, _limit: [{
                "type": "learning_node",
                "sourceKey": "rag",
                "title": "RAG",
                "description": "覆盖检索、向量库与知识库问答。",
                "href": "learn-node.html?slug=rag",
                "reason": "命中 RAG 学习需求",
            }],
            tool_search=lambda _query, _limit: [
                tool_card("dify", "Dify", "知识库应用开发。"),
                tool_card("chatdoc", "ChatDOC", "文档问答。"),
                tool_card("coze", "Coze 扣子", "应用编排。"),
            ],
        )

        result = runtime.run(AgentChatRequest(message=request), request_id="req-rag-artifacts")

        self.assertEqual("complete", result.response.execution.status)
        self.assertEqual([], result.response.execution.errors)
        self.assertIn("app.py", result.response.answer)
        self.assertIn("requirements.txt", result.response.answer)
        self.assertIn("README.md", result.response.answer)

    def test_prefetch_keeps_a_generic_domain_available_only_after_zero_results(self):
        enabled = (
            "site_tools_search",
            "site_learning_search",
            "site_workflow_suggest",
        )
        records = [
            _ToolRecord(
                step_id="step-learning",
                tool_name="site_learning_search",
                title="检索站内学习内容",
                status="completed",
                result_count=2,
                duration_ms=1,
                payload={"_phase": "broad", "_items": []},
            ),
            _ToolRecord(
                step_id="step-tools",
                tool_name="site_tools_search",
                title="检索站内工具",
                status="completed",
                result_count=0,
                duration_ms=1,
                payload={"_phase": "broad", "_items": []},
            ),
        ]

        remaining = SiteAgentLoopRuntime._tools_still_needed_after_prefetch(
            enabled,
            records,
        )

        self.assertEqual(
            ("site_tools_search", "site_workflow_suggest"),
            remaining,
        )

    def test_progress_reports_auditable_stages_without_private_reasoning(self):
        events = []
        model = ScriptedLoopModel({
            "answer": "推荐 Canva AI，因为它适合模板排版。",
            "intent": "tool_recommendation",
            "objectives": [{
                "objective": "推荐工具并说明原因",
                "status": "completed",
                "explanation": "已基于站内事实说明。",
            }],
            "selectedSourceKeys": ["canva-ai"],
            "followups": [],
        })
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="test",
            model_name="scripted",
            tool_search=lambda _query, _limit: [
                tool_card("canva-ai", "Canva AI", "适合模板排版。")
            ],
        )

        runtime.run(
            AgentChatRequest(message="推荐一个绘图工具并说明原因"),
            request_id="req-progress",
            on_progress=events.append,
        )

        self.assertEqual("understand", events[0]["stage"])
        self.assertIn("tool", {event["stage"] for event in events})
        self.assertIn("synthesize", {event["stage"] for event in events})
        self.assertIn("inspect", {event["stage"] for event in events})
        self.assertTrue(all("reasoning" not in event for event in events))

    def test_tool_budget_failure_reports_progress_without_crashing(self):
        events = []
        runtime = SiteAgentLoopRuntime(
            model=ScriptedLoopModel({}),
            provider_name="test",
            model_name="scripted",
        )
        invocation = _LoopInvocation(
            request=AgentChatRequest(message="测试工具预算"),
            history=(),
            user_context=None,
            request_id="req-tool-budget",
            on_progress=events.append,
        )
        for index in range(9):
            payload = runtime._execute_search(
                invocation,
                tool_name=f"site_test_search_{index}",
                title="检索站内学习内容",
                query=f"无结果 {index}",
                limit=3,
                search=lambda _query, _limit: [],
                error_code="LEARNING_SEARCH_FAILED",
            )

        self.assertIn("AGENT_TOOL_BUDGET_EXCEEDED", payload)
        self.assertEqual("failed", events[-1]["status"])
        self.assertEqual("AGENT_TOOL_BUDGET_EXCEEDED", events[-1]["errorCode"])

    def test_successful_domain_search_is_reused_without_duplicate_database_call(self):
        searched = 0

        def search(_query: str, _limit: int) -> list[dict[str, Any]]:
            nonlocal searched
            searched += 1
            return [tool_card("canva-ai", "Canva AI", "适合模板排版。")]

        runtime = SiteAgentLoopRuntime(
            model=ScriptedLoopModel({}),
            provider_name="test",
            model_name="scripted",
        )
        invocation = _LoopInvocation(
            request=AgentChatRequest(message="推荐设计工具"),
            history=(),
            user_context=None,
            request_id="req-search-cache",
        )

        first = runtime._execute_search(
            invocation,
            tool_name="site_tools_search",
            title="检索站内工具",
            query="设计",
            limit=3,
            search=search,
            error_code="TOOLS_SEARCH_FAILED",
        )
        second = runtime._execute_search(
            invocation,
            tool_name="site_tools_search",
            title="检索站内工具",
            query="海报设计",
            limit=3,
            search=search,
            error_code="TOOLS_SEARCH_FAILED",
        )

        self.assertIn('"status":"completed"', first)
        self.assertIn('"status":"cached"', second)
        self.assertEqual(1, searched)
        self.assertEqual(1, len(invocation.records))

    def test_specialized_domains_require_explicit_user_intent(self):
        route_tools = SiteAgentLoopRuntime._enabled_tool_names(
            "给我一条 7 天 RAG 学习路线"
        )
        workflow_tools = SiteAgentLoopRuntime._enabled_tool_names(
            "请创建并保存我的 RAG 学习工作流"
        )
        navigation_tools = SiteAgentLoopRuntime._enabled_tool_names(
            "这个工具的站内入口在哪"
        )

        self.assertNotIn("site_workflow_suggest", route_tools)
        self.assertIn("site_workflow_suggest", workflow_tools)
        self.assertIn("site_navigation_search", navigation_tools)

    def test_visible_answer_must_expand_requested_days_and_recommendation_count(self):
        invocation = _LoopInvocation(
            request=AgentChatRequest(
                message="推荐 3 个 RAG 工具，并给出 7 天路线"
            ),
            history=(),
            user_context=None,
            request_id="req-goal-coverage",
        )
        compressed = AgentLoopFinalAnswer(
            answer="已推荐工具并给出 7 天路线。",
            intent="learning_plan",
            objectives=[{
                "objective": "完成推荐和路线",
                "status": "completed",
                "explanation": "已完成。",
            }],
            selectedSourceKeys=["dify", "coze"],
        )
        expanded = compressed.model_copy(
            update={
                "answer": "\n".join(
                    [f"第 {day} 天：完成第 {day} 步。" for day in range(1, 8)]
                ),
                "selectedSourceKeys": ["dify", "coze", "chatdoc"],
            }
        )

        issues = SiteAgentLoopRuntime._answer_coverage_issues(invocation, compressed)

        self.assertEqual(2, len(issues))
        self.assertEqual([], SiteAgentLoopRuntime._answer_coverage_issues(invocation, expanded))

    def test_media_degradation_must_disclose_boundary_and_avoid_invented_facts(self):
        invocation = _LoopInvocation(
            request=AgentChatRequest(
                message="生成一张招生海报图片，包含时间、地点和报名价格"
            ),
            history=(),
            user_context=None,
            request_id="req-media-boundary",
        )
        invented = AgentLoopFinalAnswer(
            answer="活动时间是 2024 年 3 月，报名价 ¥299。",
            intent="qa",
            objectives=[{
                "objective": "设计招生海报",
                "status": "completed",
                "explanation": "已给出方案。",
            }],
        )
        honest = invented.model_copy(
            update={
                "answer": (
                    "本站不能直接生成海报图片，但可交付可直接排版的文本方案。"
                    "时间：[具体日期，例如 2024 年 X 月 X 日]；地点：[活动地点]；价格：[报名价格]。"
                )
            }
        )

        issues = SiteAgentLoopRuntime._answer_coverage_issues(invocation, invented)

        self.assertEqual(2, len(issues))
        self.assertEqual([], SiteAgentLoopRuntime._answer_coverage_issues(invocation, honest))

        unsupported_site_claim = honest.model_copy(
            update={
                "answer": honest.answer + "可以利用 Canva 和稿定等站内工具完成排版。"
            }
        )
        claim_issues = SiteAgentLoopRuntime._answer_coverage_issues(
            invocation,
            unsupported_site_claim,
        )
        self.assertEqual(1, len(claim_issues))
        self.assertIn("没有站内工具检索证据", claim_issues[0])

        invented_quota = honest.model_copy(
            update={"answer": honest.answer + "仅限前 50 名报名。"}
        )
        quota_issues = SiteAgentLoopRuntime._answer_coverage_issues(
            invocation,
            invented_quota,
        )
        self.assertEqual(1, len(quota_issues))
        self.assertIn("名额", quota_issues[0])

    def test_tool_failure_is_partial_with_stable_diagnostic(self):
        def broken_search(_query: str, _limit: int) -> list[dict[str, Any]]:
            raise RuntimeError("database password=secret should never reach the client")

        model = ScriptedLoopModel(
            {
                "answer": "站内工具检索本轮失败，因此无法可靠给出具体工具；你可以稍后重试。",
                "intent": "tool_recommendation",
                "objectives": [
                    {
                        "objective": "推荐绘图工具",
                        "status": "partial",
                        "explanation": "站内检索失败，未编造候选。",
                    },
                    {
                        "objective": "说明原因",
                        "status": "partial",
                        "explanation": "没有可靠候选可供逐项分析。",
                    },
                ],
                "selectedSourceKeys": [],
                "followups": ["稍后重试站内工具检索"],
            }
        )
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="test",
            model_name="scripted",
            tool_search=broken_search,
        )

        result = runtime.run(
            AgentChatRequest(message="推荐绘图工具并说明原因"),
            request_id="req-loop-partial",
        )

        execution = result.response.execution
        self.assertEqual("partial", execution.status)
        self.assertEqual("TOOLS_SEARCH_FAILED", execution.errors[0].code)
        self.assertEqual("req-loop-partial", execution.errors[0].diagnosticId)
        self.assertNotIn("password", execution.errors[0].message)
        self.assertEqual("failed", execution.steps[0].status)
        self.assertIn("稍后重试", result.response.answer)

    def test_model_runtime_failure_is_visible_instead_of_silent_fallback(self):
        class BrokenModel(ScriptedLoopModel):
            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                raise RuntimeError("upstream transport exploded")

        runtime = SiteAgentLoopRuntime(
            model=BrokenModel({}),
            provider_name="test",
            model_name="broken",
            tool_search=lambda _query, _limit: [],
        )

        result = runtime.run(
            AgentChatRequest(message="分析一下为什么应该选择绘图工具"),
            request_id="req-loop-failed",
        )

        self.assertEqual("failed", result.response.execution.status)
        self.assertEqual("AGENT_MODEL_LOOP_FAILED", result.response.execution.errors[0].code)
        self.assertEqual("req-loop-failed", result.response.execution.errors[0].diagnosticId)
        self.assertIn("暂时没有取得足够的可验证内容", result.response.answer)

    def test_successful_evidence_synthesis_recovers_transient_agent_loop_failure(self):
        class AgentPhaseConnectionFailureModel(ScriptedLoopModel):
            def _generate(
                self,
                messages,
                stop=None,
                run_manager=None,
                **kwargs: Any,
            ) -> ChatResult:
                if kwargs.get("response_format"):
                    return super()._generate(messages, stop, run_manager, **kwargs)
                self._calls += 1
                raise ConnectionError("temporary provider connection failure")

        model = AgentPhaseConnectionFailureModel({
            "answer": "建议从站内 RAG 学习节点开始，先掌握检索、向量库和问答流程。",
            "intent": "learning_plan",
            "objectives": [{
                "objective": "学习 RAG",
                "status": "completed",
                "explanation": "已根据站内学习内容给出起点。",
            }],
            "selectedSourceKeys": ["rag"],
            "followups": [],
        })
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="test",
            model_name="transient-failure",
            broad_prefetch=True,
            learning_search=lambda _query, _limit: [{
                "type": "learning_node",
                "sourceKey": "rag",
                "title": "RAG",
                "description": "覆盖检索、向量库与知识库问答。",
                "href": "learn-node.html?slug=rag",
                "reason": "匹配当前学习目标",
            }],
            tool_search=lambda _query, _limit: [],
        )

        result = runtime.run(
            AgentChatRequest(message="RAG 怎么学？"),
            request_id="req-loop-recovered",
        )

        self.assertEqual("complete", result.response.execution.status)
        self.assertEqual("complete", result.response.meta.outcome)
        self.assertEqual([], result.response.execution.errors)
        self.assertIsNone(result.response.meta.fallbackReason)
        self.assertEqual(["RAG"], [card.title for card in result.response.cards])
        self.assertIn("检索", result.response.answer)

    def test_invalid_structured_output_keeps_tool_results_and_diagnostic(self):
        class InvalidStructureModel(ScriptedLoopModel):
            def _generate(
                self,
                messages,
                stop=None,
                run_manager=None,
                **kwargs: Any,
            ) -> ChatResult:
                if kwargs.get("response_format"):
                    self._calls += 1
                    return ChatResult(
                        generations=[ChatGeneration(message=AIMessage(content="not-json"))]
                    )
                return super()._generate(messages, stop, run_manager, **kwargs)

        runtime = SiteAgentLoopRuntime(
            model=InvalidStructureModel({"answer": "推荐 Canva AI。"}),
            provider_name="test",
            model_name="invalid-structure",
            tool_search=lambda _query, _limit: [
                tool_card("canva-ai", "Canva AI", "适合模板排版。")
            ],
        )

        result = runtime.run(
            AgentChatRequest(message="推荐一个绘图工具并说明原因"),
            request_id="req-loop-invalid-structure",
        )

        self.assertEqual("partial", result.response.execution.status)
        self.assertEqual(1, len(result.response.cards))
        self.assertEqual(
            "AGENT_STRUCTURED_OUTPUT_INVALID",
            result.response.execution.errors[0].code,
        )
        self.assertEqual(
            "req-loop-invalid-structure",
            result.response.execution.errors[0].diagnosticId,
        )
        self.assertEqual(4, result.response.execution.modelCalls)


class AgentLoopOrchestrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_authenticated_orchestrator_reaches_real_agent_loop(self):
        model = ScriptedLoopModel(
            {
                "answer": "推荐 Canva AI，因为它适合模板排版。",
                "intent": "tool_recommendation",
                "objectives": [
                    {
                        "objective": "推荐工具并说明原因",
                        "status": "completed",
                        "explanation": "已根据站内描述说明原因。",
                    }
                ],
                "selectedSourceKeys": ["canva-ai"],
                "followups": [],
            }
        )
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="test",
            model_name="scripted",
            tool_search=lambda _query, _limit: [
                tool_card("canva-ai", "Canva AI", "适合模板排版。")
            ],
        )
        orchestrator = AgentOrchestrator(agent_loop=runtime, timeout_seconds=3)

        response = await orchestrator.respond(
            AgentChatRequest(message="推荐一个绘图工具并说明原因"),
            request_id="req-orchestrator-loop",
            provider_allowed=True,
        )

        self.assertEqual("langchain_agent", response.meta.runtime)
        self.assertEqual("complete", response.meta.outcome)
        self.assertEqual("complete", response.execution.status)
        self.assertEqual(3, response.execution.modelCalls)
        self.assertEqual("Canva AI", response.cards[0].title)

    async def test_user_owned_model_bypasses_site_cost_budget_but_keeps_admission(self):
        model = ScriptedLoopModel({
            "answer": "推荐 Canva AI，因为它适合模板排版。",
            "intent": "tool_recommendation",
            "objectives": [{
                "objective": "推荐工具并说明原因",
                "status": "completed",
                "explanation": "已根据站内描述说明原因。",
            }],
            "selectedSourceKeys": ["canva-ai"],
            "followups": [],
        })
        runtime = SiteAgentLoopRuntime(
            model=model,
            provider_name="user-model",
            model_name="scripted",
            tool_search=lambda _query, _limit: [
                tool_card("canva-ai", "Canva AI", "适合模板排版。")
            ],
        )

        class Admission:
            entered = 0

            @asynccontextmanager
            async def slot(self, _key):
                self.entered += 1
                yield

        class Cost:
            def reserve(self, *_args, **_kwargs):
                raise AssertionError("user-owned model must not use site cost budget")

        class Governance:
            admission = Admission()
            cost = Cost()

        orchestrator = AgentOrchestrator(
            governance=Governance(),
            timeout_seconds=3,
        )
        response = await orchestrator.respond(
            AgentChatRequest(message="推荐一个绘图工具并说明原因"),
            request_id="req-user-owned-no-budget",
            provider_allowed=True,
            agent_loop_override=runtime,
        )

        self.assertEqual("complete", response.meta.outcome)
        self.assertEqual(1, Governance.admission.entered)


if __name__ == "__main__":
    unittest.main()
