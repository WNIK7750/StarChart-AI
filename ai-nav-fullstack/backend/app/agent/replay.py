from collections import OrderedDict
from functools import lru_cache
from hashlib import sha256
import json
from threading import Lock
from time import monotonic
from typing import Callable

from app.agent.schemas import AgentChatRequest, AgentStructuredResponse
from app.core.config import (
    AGENT_RESPONSE_REPLAY_MAX_ENTRIES,
    AGENT_RESPONSE_REPLAY_TTL_SECONDS,
)


class AgentReplayConflict(Exception):
    pass


def request_fingerprint(payload: AgentChatRequest) -> str:
    canonical = json.dumps(
        payload.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


class AgentResponseReplayCache:
    """Small process-local cache for replaying already completed requests.

    It stores only the canonical project response, never Provider raw data,
    prompts, credentials, or full Users Context.
    """

    def __init__(
        self,
        *,
        ttl_seconds: float,
        max_entries: int,
        clock: Callable[[], float] = monotonic,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.clock = clock
        self._entries: OrderedDict[
            tuple[int, str],
            tuple[float, str, AgentStructuredResponse],
        ] = OrderedDict()
        self._lock = Lock()

    @staticmethod
    def _copy(response: AgentStructuredResponse) -> AgentStructuredResponse:
        return AgentStructuredResponse.model_validate(response.model_dump())

    def _purge_expired(self, now: float) -> None:
        expired = [
            key
            for key, (expires_at, _fingerprint, _response) in self._entries.items()
            if expires_at <= now
        ]
        for key in expired:
            self._entries.pop(key, None)

    def get(
        self,
        user_id: int,
        request_id: str,
        fingerprint: str,
    ) -> AgentStructuredResponse | None:
        with self._lock:
            now = self.clock()
            self._purge_expired(now)
            key = (user_id, request_id)
            entry = self._entries.get(key)
            if entry is None:
                return None
            _expires_at, stored_fingerprint, response = entry
            if stored_fingerprint != fingerprint:
                raise AgentReplayConflict()
            self._entries.move_to_end(key)
            return self._copy(response)

    def put(
        self,
        user_id: int,
        request_id: str,
        fingerprint: str,
        response: AgentStructuredResponse,
    ) -> None:
        with self._lock:
            now = self.clock()
            self._purge_expired(now)
            key = (user_id, request_id)
            existing = self._entries.get(key)
            if existing is not None and existing[1] != fingerprint:
                raise AgentReplayConflict()
            self._entries[key] = (
                now + self.ttl_seconds,
                fingerprint,
                self._copy(response),
            )
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)


@lru_cache(maxsize=1)
def get_agent_response_replay_cache() -> AgentResponseReplayCache:
    return AgentResponseReplayCache(
        ttl_seconds=AGENT_RESPONSE_REPLAY_TTL_SECONDS,
        max_entries=AGENT_RESPONSE_REPLAY_MAX_ENTRIES,
    )
