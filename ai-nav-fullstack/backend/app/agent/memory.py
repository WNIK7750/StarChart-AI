def load_user_agent_preferences(user_id: int | None) -> dict:
    """Reserved Agent memory read point.

    Long-term memory must stay opt-in and should only load data that belongs to
    the current authenticated user. This placeholder prevents future Agent code
    from reading user tables ad hoc.
    """
    return {}
