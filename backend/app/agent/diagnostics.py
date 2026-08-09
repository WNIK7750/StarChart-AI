from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


DiagnosticStage = Literal[
    "understand",
    "tool",
    "synthesize",
    "inspect",
    "projection",
]


@dataclass(frozen=True, slots=True)
class AgentDiagnosticNote:
    """Compact request-local debugging context for the model.

    Notes deliberately exclude provider exceptions, stack traces, prompts,
    credentials and full model answers. They exist only for the current graph
    invocation and are discarded when the request finishes.
    """

    stage: DiagnosticStage
    category: str
    attempt: int
    next_action: str
    node: str | None = None
    tool_name: str | None = None

    def model_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "stage": self.stage,
            "category": self.category[:80],
            "attempt": max(1, min(int(self.attempt), 3)),
            "nextAction": self.next_action[:500],
        }
        if self.node:
            payload["node"] = self.node[:80]
        if self.tool_name:
            payload["tool"] = self.tool_name[:80]
        return payload


@dataclass(frozen=True, slots=True)
class AgentTraceEvent:
    """Sanitized state trace used to locate the latest failing graph stage."""

    stage: str
    status: str
    title: str
    node: str | None = None
    tool_name: str | None = None
    error_code: str | None = None

    def model_payload(self) -> dict[str, str]:
        payload = {
            "stage": self.stage[:80],
            "status": self.status[:40],
            "title": self.title[:160],
        }
        if self.node:
            payload["node"] = self.node[:80]
        if self.tool_name:
            payload["tool"] = self.tool_name[:80]
        if self.error_code:
            payload["errorCode"] = self.error_code[:100]
        return payload


DOMAIN_TOOL_RECOVERY_GUIDANCE: dict[str, str] = {
    "site_learning_search": (
        "停止继续调用学习检索。优先使用其他已取得的站内证据；证据不足时，"
        "由模型提供通用概念讲解和可执行学习方法，并明确暂时无法确认具体站内学习节点。"
    ),
    "site_tools_search": (
        "停止继续调用工具目录。优先使用其他已取得的站内证据；证据不足时，"
        "由模型给出选择标准和任务拆解，不得编造具体站内工具。"
    ),
    "site_navigation_search": (
        "停止继续调用导航检索。只使用已经校验的站内卡片；没有卡片时说明入口暂时无法确认，"
        "不得生成或猜测跳转地址。"
    ),
    "site_workflow_suggest": (
        "停止继续调用工作流候选。由模型先交付可执行的文本步骤；不得声称工作流已经保存，"
        "也不得把未取证工具写入可保存草案。"
    ),
    "site_web_search": (
        "停止继续联网检索。使用现有站内证据和模型的一般知识完成可完成部分，"
        "并明确最新或外部信息仍有覆盖缺口。"
    ),
}


def domain_tool_recovery_guidance(tool_name: str) -> str:
    return DOMAIN_TOOL_RECOVERY_GUIDANCE.get(
        tool_name,
        "停止重复调用当前工具，使用已有证据完成可完成部分，并明确尚未覆盖的信息。",
    )
