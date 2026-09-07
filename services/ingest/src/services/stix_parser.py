from datetime import datetime
from typing import Any

from loguru import logger

from src.models.indicator import IndicatorType
from src.services.normalizer import detect_type

STIX_PATTERN_PREFIXES = {
    "ipv4-addr:value": IndicatorType.IPV4,
    "ipv6-addr:value": IndicatorType.IPV6,
    "domain-name:value": IndicatorType.DOMAIN,
    "url:value": IndicatorType.URL,
    "file:hashes.MD5": IndicatorType.MD5,
    "file:hashes.'SHA-1'": IndicatorType.SHA1,
    "file:hashes.'SHA-256'": IndicatorType.SHA256,
}


def _extract_pattern_value(pattern: str) -> tuple[str, IndicatorType]:
    body = pattern.strip().lstrip("[").rstrip("]")
    for prefix, indicator_type in STIX_PATTERN_PREFIXES.items():
        if body.startswith(prefix):
            value = body.split("=", 1)[-1].strip().strip("'\"")
            return value, indicator_type

    value = body.split("=", 1)[-1].strip().strip("'\"")
    return value, detect_type(value)


def parse_bundle(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []

    for obj in bundle.get("objects", []):
        if obj.get("type") != "indicator":
            continue

        pattern = obj.get("pattern", "")
        if not pattern:
            continue

        value, indicator_type = _extract_pattern_value(pattern)
        if not value:
            continue

        parsed.append(
            {
                "stix_id": obj.get("id"),
                "created_by_ref": obj.get("created_by_ref"),
                "value": value,
                "indicator_type": indicator_type,
                "labels": obj.get("labels", []),
                "confidence": obj.get("confidence", 50),
                "first_seen": _parse_time(obj.get("valid_from")),
                "raw_upstream": obj,
            }
        )

    logger.bind(count=len(parsed)).info("parsed stix bundle")
    return parsed


def _parse_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
