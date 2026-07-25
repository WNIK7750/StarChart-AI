from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class PasswordRecoverySender(Protocol):
    def send_password_recovery(
        self,
        *,
        channel: str,
        target: str,
        token: str,
        expires_at: datetime,
    ) -> bool: ...


class DisabledPasswordRecoverySender:
    """Fail-closed sender used until a real verified delivery provider is configured."""

    def send_password_recovery(
        self,
        *,
        channel: str,
        target: str,
        token: str,
        expires_at: datetime,
    ) -> bool:
        del channel, target, token, expires_at
        return False


@dataclass(frozen=True)
class PasswordRecoveryDelivery:
    channel: str
    target: str
    token: str
    expires_at: datetime


class MemoryPasswordRecoverySender:
    """Test-only sender. Production composition never selects this implementation."""

    def __init__(self) -> None:
        self.deliveries: list[PasswordRecoveryDelivery] = []

    def send_password_recovery(
        self,
        *,
        channel: str,
        target: str,
        token: str,
        expires_at: datetime,
    ) -> bool:
        self.deliveries.append(
            PasswordRecoveryDelivery(
                channel=channel,
                target=target,
                token=token,
                expires_at=expires_at,
            )
        )
        return True
