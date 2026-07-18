from functools import lru_cache

from app.users.assets.facade import UserAssetsFacade, get_user_assets_facade
from app.users.authorization.service import AuthorizationService, get_authorization_service
from app.users.preferences.facade import UserPreferencesFacade, get_user_preferences_facade


class UserContextFacade:
    def __init__(
        self,
        preferences: UserPreferencesFacade,
        authorization: AuthorizationService,
        assets: UserAssetsFacade,
    ):
        self.preferences = preferences
        self.authorization = authorization
        self.assets = assets

    def for_agent(self, user_id: int) -> dict:
        preference_context = self.preferences.get_context(user_id, "agent")
        authorization = self.authorization.user_context(user_id)
        asset_summary = self.assets.workflow_summary(user_id)
        permissions = set(authorization["permissions"])
        return {
            "preferences": preference_context["preferences"],
            "capabilities": {
                "agentChat": "agent:chat" in permissions,
                "saveWorkflow": "agent:chat" in permissions,
            },
            "assets": asset_summary,
            "meta": {
                "source": "users.context",
                "contractVersion": 1,
                "preferenceVersion": preference_context["meta"]["version"],
            },
        }


@lru_cache(maxsize=1)
def get_user_context_facade() -> UserContextFacade:
    return UserContextFacade(
        get_user_preferences_facade(),
        get_authorization_service(),
        get_user_assets_facade(),
    )
