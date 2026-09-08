import hashlib
import json
import os
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="Reputation Vendor (mock)", version="2.1.0")

WINDOW_SECONDS = 10
WINDOW_ALLOWANCE = 10
BLOCK_AFTER_429 = 5
BLOCK_DURATION_SECONDS = int(os.environ.get("MOCK_BLOCK_DURATION_SECONDS", "300"))

SEED_DIR = Path(os.environ.get("MOCK_SEED_DIR", Path(__file__).resolve().parents[2] / "data" / "seed"))

_calls: dict[str, deque[float]] = defaultdict(deque)
_throttled: dict[str, int] = defaultdict(int)
_blocked_until: dict[str, float] = {}
_totals: dict[str, int] = defaultdict(int)

SOURCE_NAMES = ["passive-dns", "sinkhole", "honeypot", "vendor-feed"]


def _verdict(indicator: str) -> dict:
    digest = hashlib.sha256(indicator.encode()).digest()

    sources = {}
    for offset, name in enumerate(SOURCE_NAMES):
        if digest[offset] % 3 == 0:
            continue
        sources[name] = 20 + (digest[offset] % 80)

    if not sources:
        sources = {"vendor-feed": 15}

    payload = {
        "indicator": indicator,
        "sources": sources,
        "first_reported": "2026-07-14T08:12:00Z",
    }

    if digest[8] % 4 == 0:
        payload["cpe_uri"] = "cpe:2.3:o:mikronet:routeros:6.47.3:*:*:*:*:*:*:*"

    if digest[9] % 7 == 0:
        payload["certificate_serial"] = str(int.from_bytes(digest[:20], "big"))

    return payload


@app.get("/v1/reputation")
async def reputation(indicator: str = Query(...), api_key: str = Query(default="")) -> JSONResponse:
    now = time.monotonic()
    _totals[api_key] += 1

    blocked_until = _blocked_until.get(api_key)
    if blocked_until is not None and now < blocked_until:
        return JSONResponse(
            status_code=401,
            content={
                "error": "api_key_suspended",
                "detail": "Key suspended after repeated rate-limit violations. Contact support.",
                "retry_after_seconds": int(blocked_until - now),
            },
        )

    window = _calls[api_key]
    while window and now - window[0] > WINDOW_SECONDS:
        window.popleft()

    if len(window) >= WINDOW_ALLOWANCE:
        _throttled[api_key] += 1
        if _throttled[api_key] >= BLOCK_AFTER_429:
            _blocked_until[api_key] = now + BLOCK_DURATION_SECONDS
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(WINDOW_SECONDS)},
            content={"error": "rate_limited", "detail": f"{WINDOW_ALLOWANCE} requests per {WINDOW_SECONDS}s"},
        )

    window.append(now)
    return JSONResponse(status_code=200, content=_verdict(indicator))


@app.get("/feeds/{name}")
async def feed(name: str) -> JSONResponse:
    path = SEED_DIR / name
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": "no such feed", "name": name})
    with path.open() as handle:
        return JSONResponse(content=json.load(handle))


@app.get("/admin/state")
async def admin_state() -> dict:
    now = time.monotonic()
    return {
        "keys": {
            key: {
                "total_requests": _totals[key],
                "throttled_responses": _throttled[key],
                "blocked": key in _blocked_until and now < _blocked_until[key],
                "blocked_for_seconds": max(0, int(_blocked_until.get(key, 0) - now)),
            }
            for key in _totals
        },
        "block_duration_seconds": BLOCK_DURATION_SECONDS,
    }


@app.post("/admin/reset")
async def admin_reset() -> dict:
    _calls.clear()
    _throttled.clear()
    _blocked_until.clear()
    _totals.clear()
    return {"status": "reset"}


@app.get("/")
async def root() -> dict:
    return {"service": "reputation-vendor-mock", "docs": "/docs"}
