def classify_intent(message: str) -> str:
    text = message.lower()
    cn = lambda *codes: "".join(chr(code) for code in codes)
    workflow_keys = [cn(0x5DE5, 0x4F5C, 0x6D41), cn(0x6D41, 0x7A0B), cn(0x65B9, 0x6848), "workflow"]
    navigation_keys = [cn(0x8DF3, 0x8F6C), cn(0x6253, 0x5F00), cn(0x53BB), cn(0x5728, 0x54EA, 0x91CC), cn(0x94FE, 0x63A5)]
    tool_keys = [cn(0x5DE5, 0x5177), cn(0x63A8, 0x8350), cn(0x54EA, 0x4E2A, 0x597D)]
    learning_keys = [cn(0x5B66, 0x4E60, 0x8DEF, 0x7EBF), cn(0x5B66, 0x4E60, 0x8BA1, 0x5212), cn(0x600E, 0x4E48, 0x5B66)]
    if any(key in text for key in workflow_keys):
        return "workflow_generation"
    if any(key in text for key in navigation_keys):
        return "navigation"
    if any(key in text for key in tool_keys):
        return "tool_recommendation"
    if any(key in text for key in learning_keys):
        return "learning_plan"
    return "qa"
