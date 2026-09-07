from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "nightjar-ingest"
    environment: str = "dev"

    mongo_url: str = "mongodb://localhost:27017"
    mongo_database: str = "nightjar"

    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "nightjar"

    otel_endpoint: str = "http://localhost:4317"
    otel_enabled: bool = True

    reputation_base_url: str = "http://localhost:9401"
    reputation_api_key: str = "rep_live_7f4a2c9e1b8d6350a1f2"
    reputation_max_concurrency: int = 4

    cpe_dictionary_path: str = "data/seed/cpe_dictionary.json"

    feed_host_allowlist: list[str] = Field(
        default=[
            "feeds.nightjar-platform.internal",
            "osint.example.org",
            "stix.example.net",
        ]
    )

    default_page_limit: int = 50
    max_page_limit: int = 10000

    stale_after_hours: int = 24

    sweep_batch_size: int = 200
    sweep_max_pages: int = 50

    webhook_signing_secret: str = "whsec_3d9f1a774b2c8e05"

    @property
    def enrichment_task_queue(self) -> str:
        return f"nightjar-ingest-{self.environment}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
