from src.config import get_settings


def enrichment_queue() -> str:
    settings = get_settings()
    return f"nightjar-ingest-{settings.environment}"


def discovery_queue() -> str:
    settings = get_settings()
    return f"nightjar-ingest-{settings.environment}"


def rollup_queue() -> str:
    settings = get_settings()
    return f"nightjar-ingest{settings.environment}"
