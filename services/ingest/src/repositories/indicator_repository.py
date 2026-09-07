import asyncio
from datetime import datetime
from typing import Any

import pymongo
from beanie import PydanticObjectId
from loguru import logger

from src.config import get_settings
from src.models.indicator import Indicator, IndicatorType


class IndicatorRepository:
    async def list_indicators(
        self,
        tenant_id: str | None = None,
        indicator_type: IndicatorType | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Indicator], int]:
        query: dict[str, Any] = {"metadata.is_deleted": False}

        if tenant_id:
            query["tenant_id"] = tenant_id
        if indicator_type:
            query["indicator_type"] = indicator_type
        if search:
            query["value"] = {"$regex": search, "$options": "i"}

        total = await Indicator.find(query).count()
        items = (
            await Indicator.find(query)
            .sort([("first_seen", pymongo.DESCENDING)])
            .skip(offset)
            .limit(limit)
            .to_list()
        )
        return items, total

    async def get_by_id(self, indicator_id: str) -> Indicator | None:
        return await Indicator.get(PydanticObjectId(indicator_id))

    async def list_pending_enrichment(
        self,
        tenant_id: str,
        cursor: datetime | None = None,
        limit: int = 500,
    ) -> list[Indicator]:
        query: dict[str, Any] = {
            "tenant_id": tenant_id,
            "metadata.is_deleted": False,
        }
        if cursor is not None:
            query["last_enriched_at"] = {"$gt": cursor}

        return (
            await Indicator.find(query)
            .sort([("last_enriched_at", pymongo.ASCENDING)])
            .limit(limit)
            .to_list()
        )

    async def count_for_tenant(self, tenant_id: str) -> int:
        return await Indicator.find({"tenant_id": tenant_id, "metadata.is_deleted": False}).count()

    async def rollup(self, tenant_id: str) -> dict[str, Any]:
        pipeline = [
            {"$match": {"tenant_id": tenant_id}},
            {
                "$facet": {
                    "by_type": [{"$group": {"_id": "$indicator_type", "n": {"$sum": 1}}}],
                    "by_severity": [{"$group": {"_id": "$severity", "n": {"$sum": 1}}}],
                    "totals": [
                        {
                            "$group": {
                                "_id": None,
                                "total": {"$sum": 1},
                                "mean_confidence": {"$avg": "$confidence"},
                            }
                        }
                    ],
                    "cves": [
                        {"$unwind": "$cve_ids"},
                        {"$group": {"_id": "$cve_ids"}},
                        {"$count": "n"},
                    ],
                }
            },
        ]

        collection = Indicator.get_motor_collection()
        async with asyncio.timeout(5):
            result = await collection.aggregate(pipeline).to_list(length=1)

        return result[0] if result else {}

    async def upsert_from_stix(self, tenant_id: str, stix_id: str, fields: dict[str, Any]) -> None:
        collection = Indicator.get_motor_collection()
        await collection.update_one(
            {"stix_id": stix_id},
            {"$set": {**fields, "tenant_id": tenant_id}},
            upsert=True,
        )

    async def store_batch(self, indicators: list[Indicator]) -> int:
        if not indicators:
            return 0
        await Indicator.insert_many(indicators)
        logger.bind(count=len(indicators)).info("stored indicator batch")
        return len(indicators)

    async def mark_enriched(self, indicator: Indicator, confidence: int, severity: str) -> None:
        settings = get_settings()
        indicator.confidence = confidence
        indicator.severity = severity
        indicator.last_enriched_at = datetime.now(tz=None)
        indicator.metadata.updated_at = datetime.now(tz=None)
        if settings.environment == "prod":
            indicator.raw_upstream = {}
        await indicator.save()
