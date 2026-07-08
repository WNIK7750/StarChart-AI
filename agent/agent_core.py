"""
agent_core.py - LangChain Agent 核心（双模型路由 + 流式 + API/Ollama双模式）

功能：
1. LLM_MODE 切换：api（DeepSeek API）/ ollama（本地模型）
2. 双模型路由：简单对话→快速模型, 复杂推理→推理模型
3. 创建 ReAct Agent（langgraph.prebuilt.create_react_agent）
4. chat() — 非流式对话 / chat_stream() — SSE 流式对话
"""

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import os
import re

# ==========================================
# 模式检测
# ==========================================
LLM_MODE = os.getenv("LLM_MODE", "ollama")  # api | ollama


# ==========================================
# LLM 工厂 — API 模式
# ==========================================
def _make_api_llm(model: str, temperature: float = 0.3):
    """用 ChatOpenAI 兼容接口连接 DeepSeek API"""
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    if not api_key or api_key.startswith("sk-你的"):
        raise RuntimeError("请先在 .env 中填写 OPENAI_API_KEY（DeepSeek API Key）")
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
    )


# ==========================================
# LLM 工厂 — Ollama 模式
# ==========================================
def _make_ollama(model_keyword: str, temperature: float = 0.3):
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        import httpx
        resp = httpx.get(f"{base_url}/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            matched = [m for m in models if model_keyword in m]
            if matched:
                return ChatOllama(model=matched[0], base_url=base_url, temperature=temperature)
    except Exception as e:
        print(f"[LLM] Ollama 查询失败：{e}")
    return None


# ==========================================
# 统一获取 LLM
# ==========================================
def get_fast_llm():
    if LLM_MODE == "api":
        try:
            return _make_api_llm(os.getenv("FAST_MODEL", "deepseek-chat"), temperature=0.3)
        except RuntimeError:
            return None
    return _make_ollama(os.getenv("FAST_MODEL", "qwen2.5:7b"), temperature=0.3)


def get_reasoning_llm():
    if LLM_MODE == "api":
        try:
            return _make_api_llm(os.getenv("REASONING_MODEL", "deepseek-reasoner"), temperature=0.15)
        except RuntimeError:
            return None
    llm = _make_ollama(os.getenv("REASONING_MODEL", "deepseek-r1:7b"), temperature=0.15)
    if llm:
        return llm
    print(f"[LLM] 推理模型不可用，降级为快速模型")
    return get_fast_llm()


# ==========================================
# 模型路由
# ==========================================
REASONING_PATTERNS = [
    r"为什么", r"分析", r"对[比比]", r"[比比]较", r"推理", r"推导", r"证明",
    r"怎么实现", r"如何实现", r"原理", r"优缺点", r"区别", r"差异",
    r"评估", r"建议", r"算法", r"架构", r"优化", r"底层", r"源码",
    r"代码生成", r"写.*代码", r"帮我写", r"生成.*(?:代码|程序|脚本)",
    r"计算", r"解释.*(?:原理|机制|过程)", r"深入", r"详解",
]


def route_model(message: str) -> dict:
    """根据消息内容决定使用哪个模型"""
    for pattern in REASONING_PATTERNS:
        if re.search(pattern, message):
            return {
                "model_type": "reasoning",
                "model_name": os.getenv("REASONING_MODEL", "deepseek-reasoner"),
                "reason": "检测到推理/分析需求",
            }
    return {
        "model_type": "fast",
        "model_name": os.getenv("FAST_MODEL", "deepseek-chat"),
        "reason": "简单对话/工具检索",
    }


# ==========================================
# System Prompt
# ==========================================
SYSTEM_PROMPT = """你是一个 AI 工具导航助手，专门帮助用户发现和选择 AI 工具。

你的知识来源于 ai-nav 网站收录的工具数据库（包含对话助手、编程开发、图像生成、写作办公、视频音频、智能搜索等分类）。

工作方式：
1. 理解用户需求（想找什么类型的工具、解决什么问题）
2. 使用 search_tools 搜索相关工具
3. 基于检索结果给出专业、有针对性的推荐

回答要求：
- 用中文回答
- 简洁清晰，突出工具的特点和适用场景
- 如果用户没有明确需求，主动询问或列出分类供选择
- 不要编造不存在的工具"""


# ==========================================
# Agent 创建
# ==========================================
def _build_agent(llm):
    from langgraph.prebuilt import create_react_agent
    from tools import ALL_TOOLS
    if llm is None:
        raise RuntimeError("LLM 不可用")
    return create_react_agent(model=llm, tools=ALL_TOOLS, prompt=SYSTEM_PROMPT)


def _history_to_messages(chat_history: list) -> list:
    messages = []
    for item in (chat_history or []):
        role = item.get("role", "")
        content = item.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


def _clean_r1_think(text: str) -> str:
    return re.sub(r"<\s*think[\s\S]*?<\s*/\s*think\s*>", "", text).strip()


# ==========================================
# 对话接口
# ==========================================
def chat(user_message: str, chat_history: list = None, mode: str = "auto") -> dict:
    if mode == "reasoning":
        route = {"model_type": "reasoning", "model_name": os.getenv("REASONING_MODEL", "deepseek-reasoner"), "reason": "用户手动推理模式"}
    else:
        route = route_model(user_message)

    llm = get_reasoning_llm() if route["model_type"] == "reasoning" else get_fast_llm()

    if llm is None:
        return {"reply": "LLM 不可用。API 模式请检查 .env 中 OPENAI_API_KEY；Ollama 模式请检查 Ollama 是否运行。", "model_name": "无", "model_type": "none", "status": "error"}

    agent = _build_agent(llm)
    messages = _history_to_messages(chat_history)
    messages.append(HumanMessage(content=user_message))
    result = agent.invoke({"messages": messages})

    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and msg.content and not isinstance(msg, HumanMessage):
            text = _clean_r1_think(msg.content)
            if text:
                return {"reply": text, "model_name": route["model_name"], "model_type": route["model_type"], "status": "ok"}

    return {"reply": "（无回复）", "model_name": route["model_name"], "model_type": route["model_type"], "status": "ok"}


def chat_stream(user_message: str, chat_history: list = None, mode: str = "auto"):
    if mode == "reasoning":
        route = {"model_type": "reasoning", "model_name": os.getenv("REASONING_MODEL", "deepseek-reasoner"), "reason": "用户手动推理模式"}
    else:
        route = route_model(user_message)
    is_reasoning = route["model_type"] == "reasoning"

    llm = get_reasoning_llm() if is_reasoning else get_fast_llm()

    if llm is None:
        yield {"type": "model", "name": "无", "is_reasoning": False}
        yield {"type": "token", "content": "LLM 不可用。API 模式请检查 .env 中 OPENAI_API_KEY；Ollama 模式请检查 Ollama 是否运行。"}
        yield {"type": "done"}
        return

    yield {"type": "model", "name": route["model_name"], "is_reasoning": is_reasoning}

    agent = _build_agent(llm)
    messages = _history_to_messages(chat_history)
    messages.append(HumanMessage(content=user_message))

    in_think = False
    try:
        for item in agent.stream({"messages": messages}, stream_mode="messages"):
            msg = item[0] if isinstance(item, tuple) else item
            metadata = item[1] if isinstance(item, tuple) and len(item) > 1 else {}
            if metadata.get("langgraph_node") != "agent":
                continue
            if not hasattr(msg, "content") or not msg.content:
                continue
            chunk = msg.content
            filtered = ""
            i = 0
            while i < len(chunk):
                if not in_think:
                    pos = chunk.lower().find("<think", i)
                    if pos >= 0:
                        filtered += chunk[i:pos]
                        end = chunk.find(">", pos)
                        in_think = True
                        i = (end + 1) if end >= 0 else len(chunk)
                    else:
                        filtered += chunk[i:]
                        i = len(chunk)
                else:
                    pos = chunk.lower().find("</think", i)
                    if pos >= 0:
                        end = chunk.find(">", pos)
                        in_think = False
                        i = (end + 1) if end >= 0 else len(chunk)
                    else:
                        i = len(chunk)
            if filtered:
                yield {"type": "token", "content": filtered}
    except Exception as e:
        yield {"type": "token", "content": f"\n[错误：{e}]"}

    yield {"type": "done"}
