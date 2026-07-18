from typing import Protocol


class PreferencesRepository(Protocol):
    def get_preferences(self, user_id: int) -> dict | None: ...

    def update_preferences(self, user_id: int, values: dict, expected_version: int) -> tuple[dict | None, bool]: ...
