import io
import json
import os
import zipfile
from typing import Any
from urllib.parse import urlparse

import httpx
from loguru import logger

ALLOWED_SCHEMES = {"http", "https"}

_feed_client = httpx.AsyncClient(timeout=None, follow_redirects=True)


class FeedFetchError(Exception):
    pass


def validate_feed_url(feed_url: str) -> str:
    parsed = urlparse(feed_url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise FeedFetchError(f"unsupported scheme: {parsed.scheme!r}")
    if not parsed.netloc:
        raise FeedFetchError("feed url has no host")
    return feed_url


async def fetch_feed(feed_url: str) -> bytes:
    url = validate_feed_url(feed_url)
    logger.bind(feed_url=url).info("fetching feed")

    response = await _feed_client.get(url)
    response.raise_for_status()
    return response.content


async def fetch_stix_bundle(feed_url: str) -> dict[str, Any]:
    body = await fetch_feed(feed_url)

    if body[:2] == b"PK":
        return _first_bundle_from_archive(body)

    return json.loads(body)


def _first_bundle_from_archive(body: bytes, dest: str = "/tmp/nightjar-feeds") -> dict[str, Any]:  # noqa: S108
    os.makedirs(dest, exist_ok=True)
    extracted: list[str] = []

    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            target = os.path.join(dest, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with archive.open(name) as source, open(target, "wb") as sink:
                sink.write(source.read())
            extracted.append(target)

    for path in extracted:
        if path.endswith(".json"):
            with open(path) as handle:
                return json.load(handle)

    raise FeedFetchError("archive contained no json bundle")
