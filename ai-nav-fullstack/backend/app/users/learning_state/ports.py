from typing import Any, Protocol


class UserLearningStateRepository(Protocol):
    def list_progress(self, user_id: int) -> list[dict[str, Any]]: ...

    def get_progress(self, user_id: int, node_slug: str) -> dict[str, Any] | None: ...

    def upsert_progress(
        self,
        user_id: int,
        node_slug: str,
        status: str,
        percent: int,
        expected_version: int | None,
        section_uids: list[str] | None = None,
        section_completed: bool | None = None,
    ) -> dict[str, Any]: ...

    def list_section_progress(self, user_id: int, node_slug: str) -> list[dict[str, Any]]: ...

    def set_section_progress(
        self,
        user_id: int,
        node_slug: str,
        section_uid: str,
        is_completed: bool,
        expected_version: int | None,
        total_sections: int,
    ) -> dict[str, Any]: ...

    def record_activity(self, user_id: int, item: dict[str, Any]) -> dict[str, Any]: ...

    def recent(self, user_id: int, limit: int, offset: int) -> list[dict[str, Any]]: ...

    def recent_count(self, user_id: int) -> int: ...

    def list_favorites(self, user_id: int, limit: int, offset: int) -> list[dict[str, Any]]: ...

    def favorites_count(self, user_id: int) -> int: ...

    def add_favorite(self, user_id: int, item: dict[str, Any]) -> dict[str, Any]: ...

    def remove_favorite(self, user_id: int, favorite_uid: str) -> bool: ...
