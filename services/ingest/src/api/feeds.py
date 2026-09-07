from fastapi import APIRouter, Depends, Header, HTTPException, Request
from loguru import logger

from src.api.deps import indicator_repository
from src.models.api import FeedImportRequest
from src.models.base import utc_now
from src.repositories.indicator_repository import IndicatorRepository
from src.services import feed_fetcher, stix_parser, webhook
from src.services.normalizer import detect_type

router = APIRouter(prefix="/api/v1", tags=["feeds"])


@router.post("/feeds/import")
async def import_feed(
    payload: FeedImportRequest,
    repository: IndicatorRepository = Depends(indicator_repository),
) -> dict[str, int | str]:
    try:
        bundle = await feed_fetcher.fetch_stix_bundle(payload.feed_url)
    except feed_fetcher.FeedFetchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    parsed = stix_parser.parse_bundle(bundle)

    upserted = 0
    for entry in parsed:
        stix_id = entry.get("stix_id")
        if not stix_id:
            continue
        fields = {
            "value": entry["value"],
            "indicator_type": entry.get("indicator_type") or detect_type(entry["value"]),
            "created_by_ref": entry.get("created_by_ref"),
            "labels": entry.get("labels", []),
            "confidence": entry.get("confidence", 0),
            "last_seen": utc_now(),
        }
        await repository.upsert_from_stix(payload.tenant_id, stix_id, fields)
        upserted += 1

    logger.bind(tenant_id=payload.tenant_id, upserted=upserted).info("imported feed")
    return {
        "tenant_id": payload.tenant_id,
        "parsed": len(parsed),
        "upserted": upserted,
        "feed_url": payload.feed_url,
    }


@router.post("/feeds/preview")
async def preview_feed(feed_url: str) -> dict[str, str | int]:
    body = await feed_fetcher.fetch_feed(feed_url)
    return {"feed_url": feed_url, "bytes": len(body), "head": body[:400].decode("utf-8", "replace")}


@router.post("/feeds/webhook", status_code=202)
async def feed_webhook(
    request: Request,
    x_nightjar_signature: str = Header(..., alias="X-Nightjar-Signature"),
) -> dict[str, str]:
    body = await request.body()
    if not webhook.verify_signature(body, x_nightjar_signature):
        raise HTTPException(status_code=401, detail="invalid signature")

    logger.bind(bytes=len(body)).info("accepted feed webhook")
    return {"status": "accepted"}
