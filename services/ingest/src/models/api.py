from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from src.models.indicator import IndicatorType

T = TypeVar("T")


class IndicatorPayload(BaseModel):
    value: str
    indicator_type: IndicatorType | None = None
    labels: list[str] = Field(default_factory=list)
    confidence: int = Field(default=50, ge=0, le=100)
    source: str = "manual"
    certificate_serial: str | None = None
    raw_upstream: dict[str, Any] = Field(default_factory=dict)


class ImportRequest(BaseModel):
    tenant_id: str
    indicators: list[IndicatorPayload]


class FeedImportRequest(BaseModel):
    tenant_id: str
    feed_url: str


class IndicatorResponse(BaseModel):
    id: str
    tenant_id: str
    value: str
    indicator_type: IndicatorType
    confidence: int
    severity: str
    labels: list[str]
    cve_ids: list[str]
    first_seen: datetime
    last_seen: datetime
    last_enriched_at: datetime | None
    raw_upstream: dict[str, Any]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int | None = None
    next_cursor: str | None = None


class TenantRollup(BaseModel):
    tenant_id: str
    total_indicators: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    mean_confidence: float
    stale_count: int
    distinct_cves: int
