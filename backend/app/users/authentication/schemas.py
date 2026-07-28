from typing import Literal

from app.users.common import StrictModel


class PublicUser(StrictModel):
    userUid: str
    username: str
    email: str | None
    phone: str | None
    accountStatus: str
    emailVerified: bool
    phoneVerified: bool
    lastLoginAt: str | None
    createdAt: str


class UsernameAvailableResponse(StrictModel):
    available: Literal[True]
    username: str


class AccessTokenResponse(StrictModel):
    accessToken: str
    tokenType: Literal["Bearer"]
    expiresIn: int


class AuthResponse(AccessTokenResponse):
    user: PublicUser


class UserResponse(StrictModel):
    user: PublicUser


class StatusResponse(StrictModel):
    status: str


class StatusMessageResponse(StatusResponse):
    message: str

