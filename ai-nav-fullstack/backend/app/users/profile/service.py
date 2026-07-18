from functools import lru_cache

from app.users.common import UsersError
from app.users.profile.avatar import AvatarProcessor, AvatarStorage
from app.users.profile.ports import ProfileRepository
from app.users.profile.repositories.sqlite import SQLiteProfileRepository


class ProfileService:
    def __init__(
        self,
        repository: ProfileRepository,
        avatar_processor: AvatarProcessor | None = None,
        avatar_storage: AvatarStorage | None = None,
    ):
        self.repository = repository
        self.avatar_processor = avatar_processor or AvatarProcessor()
        self.avatar_storage = avatar_storage or AvatarStorage()

    @staticmethod
    def _clean(values: dict) -> dict:
        return {
            key: value.strip() if isinstance(value, str) else value
            for key, value in values.items()
            if value is not None
        }

    def get_profile(self, user_id: int) -> dict:
        profile = self.repository.get_profile(user_id)
        if not profile:
            raise UsersError("PROFILE_NOT_FOUND", "用户资料不存在", 404)
        return {"profile": profile}

    def update_profile(self, user_id: int, values: dict, expected_version: int) -> dict:
        profile, updated = self.repository.update_profile(user_id, self._clean(values), expected_version)
        if not profile:
            raise UsersError("PROFILE_NOT_FOUND", "用户资料不存在", 404)
        if not updated:
            raise UsersError("PROFILE_VERSION_CONFLICT", "用户资料已在其他位置更新，请刷新后重试", 409)
        return {"profile": profile}

    def update_avatar(self, user_id: int, avatar_url: str) -> tuple[str | None, dict]:
        old_url, profile = self.repository.update_avatar(user_id, avatar_url)
        if not profile:
            raise UsersError("PROFILE_NOT_FOUND", "用户资料不存在", 404)
        return old_url, {"profile": profile}

    def upload_avatar(self, user_id: int, content: bytes, content_type: str | None) -> dict:
        avatar = self.avatar_processor.process(content, content_type)
        avatar_url, stored_path = self.avatar_storage.store(avatar.data)
        try:
            old_url, result = self.update_avatar(user_id, avatar_url)
        except Exception:
            self.avatar_storage.remove_path(stored_path)
            raise

        old_avatar_removed = self.avatar_storage.remove_managed_url(old_url, exclude=stored_path)
        return {
            "avatarUrl": avatar_url,
            "profile": result["profile"],
            "meta": {
                "originalBytes": avatar.original_bytes,
                "storedBytes": len(avatar.data),
                "originalWidth": avatar.original_width,
                "originalHeight": avatar.original_height,
                "width": avatar.width,
                "height": avatar.height,
                "format": "webp",
                "oldAvatarRemoved": old_avatar_removed,
            },
        }


@lru_cache(maxsize=1)
def get_profile_service() -> ProfileService:
    return ProfileService(SQLiteProfileRepository())
