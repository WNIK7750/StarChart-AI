from functools import lru_cache

from app.core.security import hash_token
from app.users.common import UsersError
from app.users.security.ports import SecurityRepository
from app.users.security.repositories.sqlite import SQLiteSecurityRepository


def validate_password_strength(password: str) -> str:
    if len(password) < 8 or len(password) > 128:
        raise UsersError("PASSWORD_INVALID", "密码长度必须为 8-128 位", 422)
    checks = [
        any(ch.islower() for ch in password),
        any(ch.isupper() for ch in password),
        any(ch.isdigit() for ch in password),
    ]
    if sum(checks) < 2:
        raise UsersError("PASSWORD_WEAK", "密码至少需要包含大写字母、小写字母、数字中的两类", 422)
    common = {"password", "12345678", "qwerty123", "admin123", "letmein"}
    if password.lower() in common:
        raise UsersError("PASSWORD_COMMON", "密码过于常见，请换一个更安全的密码", 422)
    return password


def normalize_security_answer(answer: str) -> str:
    value = " ".join(answer.strip().lower().split())
    if len(value) < 2 or len(value) > 80:
        raise UsersError("SECURITY_ANSWER_INVALID", "密保答案长度必须为 2-80 位", 422)
    return value


def hash_security_answer(answer: str) -> str:
    return hash_token(f"security-answer:{normalize_security_answer(answer)}")


class SecurityService:
    def __init__(self, repository: SecurityRepository):
        self.repository = repository

    def update_password(self, user_id: int, current_password: str, new_password: str) -> dict:
        validate_password_strength(new_password)
        if current_password == new_password:
            raise UsersError("PASSWORD_UNCHANGED", "新密码不能和当前密码相同", 422)
        if not self.repository.update_password(user_id, current_password, new_password):
            raise UsersError("CURRENT_PASSWORD_INVALID", "当前密码不正确", 401)
        return {"status": "ok", "message": "密码已更新，请重新登录"}

    def list_security_questions(self, user_id: int) -> dict:
        rows = self.repository.list_security_questions(user_id)
        return {"configured": bool(rows), "items": rows}

    def replace_security_questions(self, user_id: int, current_password: str, items: list[dict]) -> dict:
        questions = []
        seen = set()
        for index, item in enumerate(items, start=1):
            question = " ".join(item["question"].strip().split())
            answer = item["answer"].strip()
            if question in seen:
                raise UsersError("SECURITY_QUESTION_DUPLICATE", "密保问题不能重复", 422)
            seen.add(question)
            questions.append((index, question, hash_security_answer(answer)))
        rows = self.repository.replace_security_questions(user_id, current_password, questions)
        if rows is None:
            raise UsersError("CURRENT_PASSWORD_INVALID", "当前密码不正确", 401)
        return {"configured": True, "items": rows}


@lru_cache(maxsize=1)
def get_security_service() -> SecurityService:
    return SecurityService(SQLiteSecurityRepository())
