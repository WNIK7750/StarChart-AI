from functools import lru_cache

from app.users.common import UsersError
from app.users.preferences.ports import PreferencesRepository
from app.users.preferences.repositories.sqlite import SQLitePreferencesRepository


class PreferencesService:
    def __init__(self, repository: PreferencesRepository):
        self.repository = repository

    def get_preferences(self, user_id: int) -> dict:
        preferences = self.repository.get_preferences(user_id)
        if not preferences:
            raise UsersError("PREFERENCES_NOT_FOUND", "用户偏好不存在", 404)
        return {"preferences": preferences}

    def update_preferences(self, user_id: int, values: dict, expected_version: int) -> dict:
        clean = {key: value.strip() if isinstance(value, str) else value for key, value in values.items() if value is not None}
        preferences, updated = self.repository.update_preferences(user_id, clean, expected_version)
        if not preferences:
            raise UsersError("PREFERENCES_NOT_FOUND", "用户偏好不存在", 404)
        if not updated:
            raise UsersError("PREFERENCES_VERSION_CONFLICT", "用户偏好已在其他位置更新，请刷新后重试", 409)
        return {"preferences": preferences}


@lru_cache(maxsize=1)
def get_preferences_service() -> PreferencesService:
    return PreferencesService(SQLitePreferencesRepository())
