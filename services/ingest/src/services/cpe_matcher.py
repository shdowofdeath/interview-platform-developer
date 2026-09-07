import json
from functools import lru_cache
from pathlib import Path

from loguru import logger

from src.config import get_settings


@lru_cache
def _dictionary() -> dict[str, list[str]]:
    path = Path(get_settings().cpe_dictionary_path)
    if not path.exists():
        logger.warning(f"cpe dictionary missing at {path}")
        return {}
    with path.open() as handle:
        raw = json.load(handle)
    return {entry["cpe_uri"]: entry["cve_ids"] for entry in raw["entries"]}


def applicable_cves(asset_cpe: str) -> list[str]:
    return _dictionary().get(asset_cpe, [])


def build_cpe_uri(vendor: str, product: str, version: str) -> str:
    return f"cpe:2.3:a:{vendor}:{product}:{version}:*:*:*:*:*:*:*"
