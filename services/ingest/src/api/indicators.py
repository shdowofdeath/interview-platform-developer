from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from src.api.deps import indicator_repository, tenant_from_header
from src.models.api import ImportRequest, IndicatorResponse, Page, TenantRollup
from src.models.indicator import Indicator, IndicatorType
from src.repositories.indicator_repository import IndicatorRepository
from src.services.normalizer import detect_type

router = APIRouter(prefix="/api/v1", tags=["indicators"])


def _to_response(indicator: Indicator) -> IndicatorResponse:
    return IndicatorResponse(
        id=str(indicator.id),
        tenant_id=indicator.tenant_id,
        value=indicator.value,
        indicator_type=indicator.indicator_type,
        confidence=indicator.confidence,
        severity=indicator.severity,
        labels=indicator.labels,
        cve_ids=indicator.cve_ids,
        first_seen=indicator.first_seen,
        last_seen=indicator.last_seen,
        last_enriched_at=indicator.last_enriched_at,
        raw_upstream=indicator.raw_upstream,
    )


@router.get("/indicators", response_model=Page[IndicatorResponse])
async def list_indicators(
    tenant_id: str | None = Query(default=None),
    indicator_type: IndicatorType | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    repository: IndicatorRepository = Depends(indicator_repository),
) -> Page[IndicatorResponse]:
    items, total = await repository.list_indicators(
        tenant_id=tenant_id,
        indicator_type=indicator_type,
        search=search,
        limit=limit,
        offset=offset,
    )
    return Page[IndicatorResponse](
        items=[_to_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/indicators/{indicator_id}", response_model=IndicatorResponse)
async def get_indicator(
    indicator_id: str,
    repository: IndicatorRepository = Depends(indicator_repository),
) -> IndicatorResponse:
    indicator = await repository.get_by_id(indicator_id)
    if indicator is None:
        raise HTTPException(status_code=404, detail="indicator not found")
    return _to_response(indicator)


@router.post("/indicators/import", status_code=202)
async def import_indicators(
    payload: ImportRequest,
    repository: IndicatorRepository = Depends(indicator_repository),
) -> dict[str, int]:
    documents = [
        Indicator(
            tenant_id=payload.tenant_id,
            value=item.value,
            indicator_type=item.indicator_type or detect_type(item.value),
            labels=item.labels,
            confidence=item.confidence,
            certificate_serial=int(item.certificate_serial) if item.certificate_serial else None,
            raw_upstream=item.raw_upstream,
        )
        for item in payload.indicators
    ]
    stored = await repository.store_batch(documents)
    return {"stored": stored}


@router.get("/tenants/{tenant_id}/rollup", response_model=TenantRollup)
async def tenant_rollup(
    tenant_id: str,
    caller_tenant: str = Depends(tenant_from_header),
    repository: IndicatorRepository = Depends(indicator_repository),
) -> TenantRollup:
    if caller_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")

    try:
        raw = await repository.rollup(tenant_id)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"rollup failed for {tenant_id}: {exc}")
        return TenantRollup(
            tenant_id=tenant_id,
            total_indicators=0,
            by_type={},
            by_severity={},
            mean_confidence=0.0,
            stale_count=0,
            distinct_cves=0,
        )

    totals = (raw.get("totals") or [{}])[0]
    return TenantRollup(
        tenant_id=tenant_id,
        total_indicators=totals.get("total", 0),
        by_type={row["_id"] or "unknown": row["n"] for row in raw.get("by_type", [])},
        by_severity={row["_id"] or "unknown": row["n"] for row in raw.get("by_severity", [])},
        mean_confidence=round(totals.get("mean_confidence") or 0.0, 2),
        stale_count=0,
        distinct_cves=(raw.get("cves") or [{"n": 0}])[0].get("n", 0),
    )
