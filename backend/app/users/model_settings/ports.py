from typing import Protocol


class AgentModelSettingsRepository(Protocol):
    def get(self, user_id: int) -> dict | None: ...

    def upsert(
        self,
        user_id: int,
        values: dict,
        expected_version: int | None,
    ) -> tuple[dict | None, bool]: ...

    def delete(self, user_id: int) -> bool: ...


class AgentModelCredentialStore(Protocol):
    """Stores model credentials outside the application database."""

    def get(self, subject: str) -> str | None: ...

    def put(self, subject: str, secret: str) -> None: ...

    def delete(self, subject: str) -> bool: ...
