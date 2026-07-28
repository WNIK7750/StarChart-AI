from app.learning import get_learning_service


def search_learning_nodes(query: str, limit: int = 5) -> list[dict]:
    return get_learning_service().get_agent_context(query, limit)["nodes"]


def search_learning_cards(query: str, limit: int = 5) -> list[dict]:
    return [
        {
            "type": "learning_node",
            "sourceKey": node["slug"],
            "title": node["title"],
            "description": node["summary"],
            "href": node["href"],
            "reason": "站内学习节点",
        }
        for node in search_learning_nodes(query, limit)
    ]


def get_learning_node_context(slug: str) -> dict:
    return get_learning_service().get_node(slug)


def recommend_learning_next(slug: str) -> dict | None:
    return get_learning_service().recommend_next(slug)
