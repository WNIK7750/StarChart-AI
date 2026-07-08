"""
main.py - FastAPI 后端入口

功能：
1. POST /chat — 非流式对话（含模型信息）
2. POST /chat/stream — SSE 流式对话（含模型信息）
3. GET  /health — 健康检查
4. 首次启动时自动构建/加载知识库
"""

import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# 确保当前目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
dotenv_path = Path(__file__).parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json


# ==========================================
# 启动时初始化知识库
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """替代 on_event("startup")，使用 lifespan 事件"""
    print("[启动] 正在加载知识库...")
    from knowledge_base import parse_search_data, build_documents, build_vectorstore, CHROMA_PERSIST_DIR
    from agent_core import get_fast_llm, get_reasoning_llm

    # search-data.js 在 agent/ 的上级目录（ai-nav2/ 根目录）
    JS_PATH = str(Path(__file__).parent.parent / "search-data.js")
    tools = parse_search_data(JS_PATH)
    docs = build_documents(tools)

    # 检测 Embedding 模式是否变化（变化则强制重建）
    mode_file = Path(CHROMA_PERSIST_DIR) / ".embedding_mode"
    current_mode = os.getenv("EMBEDDING_MODE", "fake")
    force = True
    if mode_file.exists():
        saved_mode = mode_file.read_text().strip()
        if saved_mode == current_mode:
            force = False
    build_vectorstore(docs, force_rebuild=force)
    mode_file.write_text(current_mode)
    print(f"[启动] 知识库就绪（{CHROMA_PERSIST_DIR}）")

    # 预检查 LLM
    llm_mode = os.getenv("LLM_MODE", "ollama")
    fast = get_fast_llm()
    reasoning = get_reasoning_llm()
    if llm_mode == "api":
        if fast or reasoning:
            print(f"[启动] API 模式 — 就绪")
        else:
            print("[警告] API 模式但 OPENAI_API_KEY 未填写，请在 .env 中设置")
    else:
        if fast:
            print(f"[启动] Ollama 快速模型就绪")
        else:
            print(f"[启动] Ollama 快速模型不可用")
        if reasoning:
            print(f"[启动] Ollama 推理模型就绪")
        else:
            print(f"[启动] Ollama 推理模型不可用，将降级")

    yield  # 应用运行期间


app = FastAPI(title="AI Nav Agent", version="1.0", lifespan=lifespan)

# CORS - 允许前端跨域调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 请求模型
# ==========================================
class ChatRequest(BaseModel):
    message: str
    history: list = []
    mode: str = "auto"  # "auto" = 智能路由, "reasoning" = 强制推理模型


# ==========================================
# 接口
# ==========================================
@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-nav-agent"}


@app.post("/chat")
async def chat(req: ChatRequest):
    """非流式对话（返回完整回复 + 模型信息）"""
    try:
        from agent_core import chat
        result = chat(req.message, req.history, req.mode)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"reply": f"Agent 错误：{e}", "model_name": "无", "model_type": "error", "status": "error"}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE 流式对话"""
    from agent_core import chat_stream

    def event_generator():
        for chunk in chat_stream(req.message, req.history, req.mode):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==========================================
# 静态文件服务（开发/生产通用）
# ==========================================
STATIC_DIR = str(Path(__file__).parent.parent)  # ai-nav2/ 根目录
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


# ==========================================
# 运行
# ==========================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
