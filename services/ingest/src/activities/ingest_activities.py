from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger
from temporalio import activity

from src.config import get_settings
from src.models.indicator import Indicator, IndicatorType, SourceConfidence
from src.observability.tracing import get_tracer, record_enrichment_attributes
from src.repositories.indicator_repository import IndicatorRepository
from src.services import confidence, cpe_matcher, feed_fetcher, reputation_client, stix_parser
from src.services.normalizer import detect_type


@dataclass
class FetchFeedInput:
    tenant_id: str
    feed_url: str


@dataclass
class EnrichInput:
    tenant_id: str
    indicators: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class StoreInput:
    tenant_id: str
    indicators: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SweepInput:
    tenant_id: str


@dataclass
class SweepResult:
    tenant_id: str
    pages: int
    scanned: int
    reenriched: int
    failed: int


@activity.defn
async def fetch_feed_activity(payload: FetchFeedInput) -> list[dict[str, Any]]:
    bundle = await feed_fetcher.fetch_stix_bundle(payload.feed_url)
    parsed = stix_parser.parse_bundle(bundle)

    for entry in parsed:
        entry["tenant_id"] = payload.tenant_id
        if entry.get("first_seen") is not None:
            entry["first_seen"] = entry["first_seen"].isoformat()

    logger.bind(tenant_id=payload.tenant_id, count=len(parsed)).info("fetched feed")
    return parsed


@activity.defn
async def enrich_batch_activity(payload: EnrichInput) -> list[dict[str, Any]]:
    tracer = get_tracer("nightjar.enrich")
    enriched: list[dict[str, Any]] = []

    for entry in payload.indicators:
        with tracer.start_as_current_span("enrich_indicator") as span:
            record_enrichment_attributes(span, entry, reputation_client._settings.reputation_base_url)

            try:
                verdict = await reputation_client.lookup(entry["value"])
            except reputation_client.ReputationUnavailable as exc:
                raise RuntimeError(f"reputation upstream unavailable: {exc}") from exc

            sources = [
                SourceConfidence(source=name, confidence=score)
                for name, score in verdict.get("sources", {}).items()
            ]
            entry["source_confidence"] = [source.model_dump(mode="json") for source in sources]
            entry["confidence"] = confidence.aggregate(sources)
            entry["severity"] = confidence.severity_for(entry["confidence"])

            if verdict.get("cpe_uri"):
                entry["cpe_uri"] = verdict["cpe_uri"]
                entry["cve_ids"] = cpe_matcher.applicable_cves(verdict["cpe_uri"])

            enriched.append(entry)

    return enriched


@activity.defn
async def store_batch_activity(payload: StoreInput) -> int:
    repository = IndicatorRepository()
    documents: list[Indicator] = []

    for entry in payload.indicators:
        raw_type = entry.get("indicator_type")
        indicator_type = IndicatorType(raw_type) if raw_type else detect_type(entry["value"])

        documents.append(
            Indicator(
                tenant_id=payload.tenant_id,
                value=entry["value"],
                indicator_type=indicator_type,
                stix_id=entry.get("stix_id"),
                created_by_ref=entry.get("created_by_ref"),
                confidence=entry.get("confidence", 0),
                severity=entry.get("severity", "unknown"),
                labels=entry.get("labels", []),
                cve_ids=entry.get("cve_ids", []),
                cpe_uri=entry.get("cpe_uri"),
                certificate_serial=entry.get("certificate_serial"),
                raw_upstream=entry.get("raw_upstream", {}),
            )
        )

    return await repository.store_batch(documents)


@activity.defn
async def sweep_stale_activity(payload: SweepInput) -> SweepResult:
    settings = get_settings()
    repository = IndicatorRepository()

    cursor: datetime | None = None
    pages = 0
    scanned = 0
    reenriched = 0
    failed = 0

    while pages < settings.sweep_max_pages:
        batch = await repository.list_pending_enrichment(
            payload.tenant_id,
            cursor=cursor,
            limit=settings.sweep_batch_size,
        )
        if not batch:
            break

        pages += 1
        scanned += len(batch)

        for indicator in batch:
            if not indicator.is_stale:
                continue
            try:
                verdict = await reputation_client.lookup(indicator.value)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"sweep enrichment failed for {indicator.value}: {exc}")
                failed += 1
                continue

            sources = [
                SourceConfidence(source=name, confidence=score)
                for name, score in verdict.get("sources", {}).items()
            ]
            score = confidence.aggregate(sources)
            await repository.mark_enriched(indicator, score, confidence.severity_for(score))
            reenriched += 1

        cursor = batch[-1].last_enriched_at

    logger.bind(
        tenant_id=payload.tenant_id,
        pages=pages,
        scanned=scanned,
        reenriched=reenriched,
        failed=failed,
    ).info("sweep finished")

    return SweepResult(
        tenant_id=payload.tenant_id,
        pages=pages,
        scanned=scanned,
        reenriched=reenriched,
        failed=failed,
    )


@activity.defn
async def list_tenant_feeds_activity(tenant_id: str) -> list[str]:
    from src.models.indicator import Tenant

    tenant = await Tenant.find_one({"tenant_id": tenant_id})
    return tenant.feed_urls if tenant else []
