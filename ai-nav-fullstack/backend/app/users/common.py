from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResponseModel(BaseModel):
    """Field-level response allowlist; unknown service fields are never serialized."""

    model_config = ConfigDict(extra="ignore")


class UsersError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def users_error_detail(exc: UsersError) -> dict[str, str]:
    return {"code": exc.code, "message": exc.message}
