"""
knowledge_base.py - RAG 知识库模块

功能：
1. 解析 search-data.js，提取工具数据
2. 格式化为自然语言文档
3. 用 Embedding 模型向量化，存入 Chroma
4. 提供检索接口（retriever）

运行：python knowledge_base.py （首次构建索引）
"""

import os
import re
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ==========================================
# 配置：从 .env 读取
# ==========================================
BASE_DIR = Path(__file__).parent
dotenv_path = BASE_DIR / ".env"
if dotenv_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=dotenv_path)

CHROMA_PERSIST_DIR = str(BASE_DIR / "chroma_db")
SEARCH_DATA_PATH = str(BASE_DIR.parent.parent / "search-data.js")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
EMBEDDING_MODE = os.getenv("EMBEDDING_MODE", "fake")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn")
LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# 导入 Chroma（确保 langchain-chroma 已安装）
from langchain_chroma import Chroma


# ==========================================
# 1. 解析 search-data.js
# ==========================================
def parse_search_data(js_path: str) -> list:
    """
    从 search-data.js 提取工具数据。
    用逐行解析方式，兼容 JS 注释和尾逗号。
    """
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取 const TOOLS = [ ... ] 之间的内容
    match = re.search(r"const\s+TOOLS\s*=\s*\[(.*?)\]\s*;", content, re.DOTALL)
    if not match:
        raise ValueError("无法从 search-data.js 提取 TOOLS 数组")

    array_body = match.group(1)

    # 按 { } 分割成每个工具对象
    objects = re.split(r"\}\s*,\s*\{", array_body)

    tools = []
    for obj_text in objects:
        tool = {}
        # 提取所有 key: 'value' 或 key: "value" 或 key: value（字符串/数组）
        # 字符串值
        for m in re.finditer(r"(\w+)\s*:\s*'([^']*)'", obj_text):
            tool[m.group(1)] = m.group(2)
        for m in re.finditer(r'(\w+)\s*:\s*"([^"]*)"', obj_text):
            tool[m.group(1)] = m.group(2)
        # 数组值 ['a', 'b']
        for m in re.finditer(r"(\w+)\s*:\s*\[((?:\s*'[^']*'\s*,?\s*)*)\]", obj_text):
            arr_str = m.group(2)
            arr = re.findall(r"'([^']*)'", arr_str)
            tool[m.group(1)] = arr
        if tool.get("name"):  # 只要有 name 就认为是有效工具
            tools.append(tool)

    print(f"[解析] 共 {len(tools)} 条工具数据")
    return tools


# ==========================================
# 2. 格式化为 Document
# ==========================================
def format_tool_to_doc(tool: dict) -> str:
    parts = [f"工具名称：{tool.get('name', '')}"]
    if tool.get("maker"):
        parts.append(f"开发商：{tool['maker']}")
    if tool.get("catName"):
        parts.append(f"分类：{tool['catName']}")
    if tool.get("desc"):
        parts.append(f"简介：{tool['desc']}")
    if tool.get("tags"):
        tags = tool["tags"] if isinstance(tool["tags"], list) else [str(tool["tags"])]
        parts.append(f"标签：{'、'.join(tags)}")
    # url 是 JS 动态引用，跳过
    return "\n".join(parts)


def build_documents(tools: list) -> list:
    from langchain_core.documents import Document
    docs = []
    for t in tools:
        docs.append(Document(
            page_content=format_tool_to_doc(t),
            metadata={
                "id": t.get("id", ""),
                "name": t.get("name", ""),
                "cat": t.get("cat", ""),
                "catName": t.get("catName", ""),
                "url": t.get("url", ""),
            },
        ))
    print(f"[文档] 共 {len(docs)} 个 Document")
    return docs


# ==========================================
# 3. Embedding
# ==========================================
def get_embeddings():
    # api 模式优先
    if EMBEDDING_MODE == "api" and EMBEDDING_API_KEY:
        print(f"[Embedding] API 模式：{EMBEDDING_BASE_URL} / {EMBEDDING_MODEL_NAME}")
        return _SiliconFlowEmbeddings(EMBEDDING_MODEL_NAME, EMBEDDING_API_KEY, EMBEDDING_BASE_URL)

    if EMBEDDING_MODE == "api" and not EMBEDDING_API_KEY:
        print("[Embedding] API 模式但 EMBEDDING_API_KEY 未填写，降级到 ollama")

    if EMBEDDING_MODE == "ollama":
        print(f"[Embedding] Ollama 模式：{OLLAMA_EMBED_MODEL}")
        return _OllamaEmbeddings(OLLAMA_EMBED_MODEL, OLLAMA_BASE_URL)

    if EMBEDDING_MODE == "local":
        print(f"[Embedding] 本地模式：{LOCAL_EMBEDDING_MODEL}")
        return _LocalEmbeddings(LOCAL_EMBEDDING_MODEL)

    print("[Embedding] Fake 模式（测试用）")
    return _FakeEmbeddings()


class _FakeEmbeddings:
    """Fake Embedding，用 hash 生成向量，无需 API Key。"""
    def _to_vec(self, text: str, dim: int = 384) -> list:
        import hashlib, struct, math
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = []
        for i in range(dim):
            chunk = h[(i * 4) % 32 : ((i * 4) % 32) + 4]
            if len(chunk) < 4:
                chunk = chunk + b"\x00" * (4 - len(chunk))
            val = struct.unpack(">i", chunk)[0] / (2 ** 31)
            vec.append(val)
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm > 0 else [0.0] * dim

    def embed_documents(self, texts):
        return [self._to_vec(t) for t in texts]

    def embed_query(self, text):
        return self._to_vec(text)


class _LocalEmbeddings:
    """本地 sentence-transformers Embedding。
    模型首次加载会自动下载（约118MB），之后缓存。"""
    _instances = {}  # 单例缓存

    def __new__(cls, model_name: str):
        if model_name not in cls._instances:
            obj = super().__new__(cls)
            from sentence_transformers import SentenceTransformer
            print(f"[Embedding] 首次加载 {model_name}（可能需要下载，约118MB）...")
            obj._model = SentenceTransformer(model_name)
            obj._model_name = model_name
            cls._instances[model_name] = obj
            print(f"[Embedding] 模型就绪")
        return cls._instances[model_name]

    def embed_documents(self, texts):
        return self._model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True
        ).tolist()

    def embed_query(self, text):
        return self._model.encode(
            text, convert_to_numpy=True, normalize_embeddings=True
        ).tolist()


class _OllamaEmbeddings:
    """通过 Ollama Embedding API 向量化（nomic-embed-text）。"""

    def __init__(self, model_name: str, base_url: str):
        import httpx
        self._model = model_name
        self._url = f"{base_url}/api/embed"
        self._client = httpx.Client(timeout=30)

        # 预热检查
        try:
            r = self._client.post(self._url, json={"model": model_name, "input": "test"})
            if r.status_code == 200:
                dim = len(r.json()["embeddings"][0])
                print(f"[Embedding] Ollama 就绪，向量维度={dim}")
            else:
                raise RuntimeError(f"Ollama Embedding 返回 {r.status_code}")
        except Exception as e:
            print(f"[Embedding] 警告：预热失败 ({e})，将在首次调用时重试")

    def embed_documents(self, texts):
        results = []
        for text in texts:
            r = self._client.post(self._url, json={"model": self._model, "input": text})
            if r.status_code != 200:
                raise RuntimeError(f"Ollama Embedding 错误：{r.text}")
            results.append(r.json()["embeddings"][0])
        return results

    def embed_query(self, text):
        return self.embed_documents([text])[0]


class _SiliconFlowEmbeddings:
    """直接 HTTP 调用 SiliconFlow Embedding API（避免 langchain_openai 参数兼容问题）。"""

    def __init__(self, model: str, api_key: str, base_url: str):
        import httpx
        self._model = model
        self._url = f"{base_url}/embeddings"
        self._client = httpx.Client(timeout=30, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })
        # 预热测试
        try:
            r = self._client.post(self._url, json={"model": model, "input": "test"})
            if r.status_code == 200:
                dim = len(r.json()["data"][0]["embedding"])
                print(f"[Embedding] SiliconFlow 就绪，向量维度={dim}")
            else:
                print(f"[Embedding] 预热返回 {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"[Embedding] 预热失败 ({e})")

    def _embed_batch(self, texts):
        r = self._client.post(self._url, json={
            "model": self._model,
            "input": texts,
        })
        if r.status_code != 200:
            raise RuntimeError(f"SiliconFlow Embedding 错误：{r.text[:300]}")
        data = r.json()
        return [item["embedding"] for item in data["data"]]

    def embed_documents(self, texts):
        return self._embed_batch(texts)

    def embed_query(self, text):
        return self._embed_batch([text])[0]


# ==========================================
# 4. 构建 / 加载 Chroma
# ==========================================
def build_vectorstore(docs, force_rebuild=False):
    db_path = Path(CHROMA_PERSIST_DIR)
    if db_path.exists() and list(db_path.glob("*")) and not force_rebuild:
        print("[Chroma] 已有索引，直接加载")
        return load_vectorstore()

    print(f"[Chroma] 构建中（{len(docs)} 个文档）...")
    embeddings = get_embeddings()
    vs = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    print(f"[Chroma] 完成，已保存到 {CHROMA_PERSIST_DIR}")
    return vs


def load_vectorstore():
    embeddings = get_embeddings()
    vs = Chroma(persist_directory=CHROMA_PERSIST_DIR, embedding_function=embeddings)
    print(f"[Chroma] 已加载，共 {vs._collection.count()} 条")
    return vs


def get_retriever(vectorstore, k: int = 5):
    return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": k})


# ==========================================
# 5. 测试
# ==========================================
def test_retrieval(retriever, query="有什么好用的深度学习框架？"):
    print(f"\n[测试] 查询：{query}")
    docs = retriever.get_relevant_documents(query)
    for i, d in enumerate(docs, 1):
        print(f"  {i}. {d.metadata.get('name','?')}（{d.metadata.get('catName','')}）")
    return docs


# ==========================================
# 主流程
# ==========================================
if __name__ == "__main__":
    print("=" * 50)
    print("RAG 知识库构建")
    print("=" * 50)

    tools = parse_search_data(SEARCH_DATA_PATH)
    docs = build_documents(tools)
    vs = build_vectorstore(docs, force_rebuild=False)
    retriever = get_retriever(vs, k=3)
    test_retrieval(retriever, "Python 机器学习框架推荐")

    print("\n完成！")
    print(f"  向量库：{CHROMA_PERSIST_DIR}")
    print(f"  Embedding：{EMBEDDING_MODE}")
