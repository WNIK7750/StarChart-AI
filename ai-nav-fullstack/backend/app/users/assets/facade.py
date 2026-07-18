from functools import lru_cache

from app.users.assets.service import AssetsService, get_assets_service


class UserAssetsFacade:
    def __init__(self, service: AssetsService):
        self.service = service

    def save_workflow(self, user_id: int, payload: dict, idempotency_key: str, context: dict) -> dict:
        return self.service.create_workflow(user_id, payload, idempotency_key, context)

    def workflow_summary(self, user_id: int, limit: int = 3) -> dict:
        return self.service.summary(user_id, limit)


@lru_cache(maxsize=1)
def get_user_assets_facade() -> UserAssetsFacade:
    return UserAssetsFacade(get_assets_service())
