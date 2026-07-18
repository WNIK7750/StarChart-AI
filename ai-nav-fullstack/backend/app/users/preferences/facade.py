from functools import lru_cache
from typing import Literal

from app.users.preferences.service import PreferencesService, get_preferences_service
from app.users.privacy.service import PrivacyService, get_privacy_service


PreferenceConsumer = Literal["learning", "tools", "agent"]

CONSUMER_FIELDS: dict[PreferenceConsumer, tuple[str, ...]] = {
    "learning": ("language", "cnFirst", "freeFirst", "showExternalResources"),
    "tools": ("language", "cnFirst", "freeFirst", "showExternalResources"),
    "agent": ("language", "cnFirst", "freeFirst", "showExternalResources"),
}


class UserPreferencesFacade:
    def __init__(self, service: PreferencesService, privacy: PrivacyService | None = None):
        self.service = service
        self.privacy = privacy or get_privacy_service()

    def get_context(self, user_id: int, consumer: PreferenceConsumer) -> dict:
        preferences = self.service.get_preferences(user_id)["preferences"]
        projected = {field: preferences[field] for field in CONSUMER_FIELDS[consumer]}
        if consumer == "agent":
            projected["agentMemoryEnabled"] = self.privacy.has_current_consent(user_id, "agent_memory")
        return {
            "preferences": projected,
            "meta": {
                "source": "users.preferences",
                "contractVersion": 1,
                "consumer": consumer,
                "version": preferences["version"],
            },
        }


@lru_cache(maxsize=1)
def get_user_preferences_facade() -> UserPreferencesFacade:
    return UserPreferencesFacade(get_preferences_service(), get_privacy_service())
