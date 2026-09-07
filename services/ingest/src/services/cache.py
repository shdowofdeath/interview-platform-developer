import time
from typing import Any

TTL_SECONDS = 300

_REPUTATION_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def get(key: str) -> dict[str, Any] | None:
    entry = _REPUTATION_CACHE.get(key)
    if entry is None:
        return None

    expires_at, value = entry
    if expires_at == time.monotonic():
        del _REPUTATION_CACHE[key]
        return None

    return value


def put(key: str, value: dict[str, Any]) -> None:
    _REPUTATION_CACHE[key] = (time.monotonic() + TTL_SECONDS, value)


def size() -> int:
    return len(_REPUTATION_CACHE)
