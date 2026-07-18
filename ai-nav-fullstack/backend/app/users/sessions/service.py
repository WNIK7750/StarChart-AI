from functools import lru_cache

from app.users.common import UsersError
from app.users.sessions.ports import SessionsRepository
from app.users.sessions.repositories.sqlite import SQLiteSessionsRepository


class SessionsService:
    def __init__(self, repository: SessionsRepository):
        self.repository = repository

    def list_sessions(self, user_id: int, page: int = 1, page_size: int = 20, current_refresh_token_hash: str | None = None) -> dict:
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        total = self.repository.count_sessions(user_id)
        return {
            "items": self.repository.list_sessions(user_id, page_size, (page - 1) * page_size, current_refresh_token_hash),
            "meta": {
                "page": page,
                "pageSize": page_size,
                "totalCount": total,
                "hasNext": page * page_size < total,
                "source": "users.sessions",
                "contractVersion": 2,
            },
        }

    def revoke_session(self, user_id: int, session_uid: str) -> dict:
        if not self.repository.revoke_session(user_id, session_uid):
            raise UsersError("SESSION_NOT_FOUND", "登录会话不存在", 404)
        return {"status": "ok"}

    def revoke_other_sessions(self, user_id: int, current_refresh_token_hash: str | None = None) -> dict:
        revoked_count = self.repository.revoke_other_sessions(user_id, current_refresh_token_hash)
        return {"status": "ok", "revokedCount": revoked_count}


@lru_cache(maxsize=1)
def get_sessions_service() -> SessionsService:
    return SessionsService(SQLiteSessionsRepository())
