"""
tools.py - Agent 可调用的工具函数

Agent 通过这些工具与知识库和外部系统交互：
1. search_tools - 从 RAG 知识库检索相关工具
2. get_tool_detail - 获取某个工具的详细信息
"""

from langchain.tools import tool


@tool
def search_tools(query: str) -> str:
    """在 AI 工具导航库中搜索相关工具。
    当用户询问"有什么XX工具"、"推荐XX工具"、"XX工具哪个好"时使用此工具。

    Args:
        query: 搜索关键词，如 "深度学习框架"、"免费对话AI"、"代码补全工具"
    """
    from knowledge_base import load_vectorstore, get_retriever

    vs = load_vectorstore()
    retriever = get_retriever(vs, k=5)
    docs = retriever.invoke(query)

    if not docs:
        return "未找到相关工具。"

    results = []
    for i, doc in enumerate(docs, 1):
        name = doc.metadata.get("name", "未知")
        cat = doc.metadata.get("catName", "")
        desc_line = ""
        for line in doc.page_content.split("\n"):
            if line.startswith("简介："):
                desc_line = line
                break
        results.append(f"{i}. {name}（{cat}）- {desc_line}")

    return "\n".join(results)


@tool
def get_tool_detail(tool_name: str) -> str:
    """获取某个工具的详细信息。
    当用户想了解某个特定工具的详细情况时使用。

    Args:
        tool_name: 工具名称，如 "Kimi"、"通义千问"、"Midjourney"
    """
    from knowledge_base import load_vectorstore, get_retriever

    vs = load_vectorstore()
    # 用名称精确搜索
    retriever = get_retriever(vs, k=1)
    docs = retriever.invoke(tool_name)

    if not docs:
        return f"未找到名为 '{tool_name}' 的工具。"

    return docs[0].page_content


@tool
def list_categories() -> str:
    """列出所有工具分类及每个分类下的工具数量。
    当用户想了解有哪些分类、或想浏览某个分类时使用。
    """
    from knowledge_base import load_vectorstore
    import re

    vs = load_vectorstore()
    count = vs._collection.count()
    # 从 metadata 统计分类
    all_meta = vs._collection.get(include=["metadatas"])
    cats = {}
    for meta in all_meta["metadatas"]:
        cat_name = meta.get("catName", "未分类")
        cats[cat_name] = cats.get(cat_name, 0) + 1

    lines = ["工具分类概览（共 {} 条）：".format(count)]
    for cat, num in sorted(cats.items(), key=lambda x: -x[1]):
        lines.append(f"  - {cat}：{num} 个工具")
    lines.append("\n提示：可以告诉我你感兴趣的分类，我来推荐具体工具。")
    return "\n".join(lines)


# 所有工具列表，供 agent_core.py 使用
ALL_TOOLS = [search_tools, get_tool_detail, list_categories]
