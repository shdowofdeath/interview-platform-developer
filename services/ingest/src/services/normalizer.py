from src.models.indicator import IndicatorType

HASH_LENGTHS = {
    32: IndicatorType.MD5,
    40: IndicatorType.SHA1,
    64: IndicatorType.SHA256,
}


def normalize_value(value: str) -> str:
    return value.strip()


def detect_type(value: str) -> IndicatorType:
    candidate = normalize_value(value)

    if len(candidate) in HASH_LENGTHS:
        return HASH_LENGTHS[len(candidate)]

    if candidate.startswith(("http://", "https://")):
        return IndicatorType.URL

    if ":" in candidate and candidate.count(":") >= 2:
        return IndicatorType.IPV6

    parts = candidate.split(".")
    if len(parts) == 4 and all(part.isdigit() for part in parts):
        return IndicatorType.IPV4

    if "." in candidate:
        return IndicatorType.DOMAIN

    return IndicatorType.UNKNOWN


def dedupe_key(tenant_id: str, value: str) -> str:
    return f"{tenant_id}:{normalize_value(value)}"


def matches(indicator_value: str, observed_value: str) -> bool:
    return normalize_value(indicator_value) == normalize_value(observed_value)
