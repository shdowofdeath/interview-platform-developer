from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

import pymongo
from pydantic import BaseModel, Field

from src.config import get_settings
from src.models.base import BaseTenantDocument, utc_now


class IndicatorType(StrEnum):
    IPV4 = "ipv4-addr"
    IPV6 = "ipv6-addr"
    DOMAIN = "domain-name"
    URL = "url"
    MD5 = "file-md5"
    SHA1 = "file-sha1"
    SHA256 = "file-sha256"
    CERTIFICATE = "x509-certificate"
    UNKNOWN = "unknown"


class SourceConfidence(BaseModel):
    source: str
    confidence: int = Field(ge=0, le=100)
    observed_at: datetime = Field(default_factory=utc_now)


class Indicator(BaseTenantDocument):
    value: str
    indicator_type: IndicatorType = IndicatorType.UNKNOWN

    stix_id: str | None = None
    created_by_ref: str | None = None

    source_confidence: list[SourceConfidence] = Field(default_factory=list)
    confidence: int = 0
    severity: str = "unknown"

    labels: list[str] = Field(default_factory=list)
    cve_ids: list[str] = Field(default_factory=list)
    cpe_uri: str | None = None

    certificate_serial: int | None = None

    first_seen: datetime = Field(default_factory=utc_now)
    last_seen: datetime = Field(default_factory=utc_now)
    last_enriched_at: datetime | None = None

    raw_upstream: dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "indicators"
        indexes = [
            [("first_seen", pymongo.DESCENDING)],
            [("value", pymongo.ASCENDING)],
            [("stix_id", pymongo.ASCENDING)],
        ]

    @property
    def is_stale(self) -> bool:
        if self.last_enriched_at is None:
            return True
        cutoff = datetime.utcnow() - timedelta(hours=get_settings().stale_after_hours)
        return self.last_enriched_at < cutoff


class Tenant(BaseTenantDocument):
    name: str
    feed_urls: list[str] = Field(default_factory=list)
    enabled: bool = True

    class Settings:
        name = "tenants"
