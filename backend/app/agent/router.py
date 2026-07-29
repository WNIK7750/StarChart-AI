def classify_intent(message: str) -> str:
    text = " ".join(message.lower().split())
    definition_hints = ("是什么", "什么意思", "介绍", "解释", "原理")
    navigation_hints = (
        "跳转",
        "打开",
        "前往",
        "带我去",
        "去往",
        "在哪里",
        "在哪儿",
        "入口",
    )
    learning_hints = (
        "学习路线",
        "学习计划",
        "怎么学",
        "如何学习",
        "从哪里学",
        "入门路径",
    )
    workflow_hints = ("工作流", "流程", "workflow")
    workflow_action_hints = ("帮我", "生成", "创建", "设计", "制定", "做", "给我")
    tool_choice_hints = (
        "推荐",
        "哪个工具",
        "哪款工具",
        "什么工具",
        "工具哪个好",
        "选择",
        "帮我找",
    )

    if "带我去学习" in text:
        return "learning_plan"
    if any(hint in text for hint in navigation_hints):
        return "navigation"
    if any(hint in text for hint in definition_hints):
        return "qa"
    if any(hint in text for hint in learning_hints):
        return "learning_plan"
    if (
        any(hint in text for hint in workflow_hints)
        or ("方案" in text and any(hint in text for hint in workflow_action_hints))
    ):
        return "workflow_generation"
    if (
        "工具" in text and any(hint in text for hint in tool_choice_hints)
    ) or (
        "推荐" in text
        and any(hint in text for hint in (" ai", "ai ", "模型", "软件", "应用", "平台"))
    ):
        return "tool_recommendation"
    return "qa"
