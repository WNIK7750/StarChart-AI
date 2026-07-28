def format_duration(minutes: int) -> str:
    if minutes <= 0:
        return "待补充"
    if minutes < 60:
        return f"{minutes} min"
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes / 60:.1f}h"


def site_learning_node_href(slug: str) -> str:
    return f"learn-node.html?slug={slug}"
