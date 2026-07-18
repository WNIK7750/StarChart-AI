from app.users.preferences.facade import UserPreferencesFacade, get_user_preferences_facade


def load_user_agent_preferences(user_id: int | None, facade: UserPreferencesFacade | None = None) -> dict:
    if user_id is None:
        return {"preferences": {}, "meta": {"source": "anonymous", "contractVersion": 1, "consumer": "agent"}}
    return (facade or get_user_preferences_facade()).get_context(user_id, "agent")
