from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.activities.ingest_activities import (
        EnrichInput,
        FetchFeedInput,
        StoreInput,
        enrich_batch_activity,
        fetch_feed_activity,
        list_tenant_feeds_activity,
        store_batch_activity,
    )
    from src.queues import rollup_queue

DEFAULT_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_attempts=0,
)

ENRICH_BATCH_SIZE = 500


@dataclass
class IngestInput:
    tenant_id: str
    feed_urls: list[str] = field(default_factory=list)


@dataclass
class IngestResult:
    run_id: str
    tenant_id: str
    started_at: str
    fetched: int
    stored: int
    severity_buckets: dict[str, int] = field(default_factory=dict)


@workflow.defn(name="NightjarIngestWorkflow")
class NightjarIngestWorkflow:
    @workflow.run
    async def run(self, payload: IngestInput) -> IngestResult:
        run_id = str(uuid4())
        started_at = datetime.now(UTC).isoformat()

        feed_urls = payload.feed_urls
        if not feed_urls:
            feed_urls = await workflow.execute_activity(
                list_tenant_feeds_activity,
                payload.tenant_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY,
            )

        fetched: list[dict[str, Any]] = []
        for feed_url in feed_urls:
            batch = await workflow.execute_activity(
                fetch_feed_activity,
                FetchFeedInput(tenant_id=payload.tenant_id, feed_url=feed_url),
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=DEFAULT_RETRY,
            )
            fetched.extend(batch)

        severity_buckets: dict[str, int] = {}
        by_value: dict[str, dict[str, Any]] = {}
        for entry in fetched:
            by_value[entry["value"].strip()] = entry
            bucket = entry.get("severity", "unknown")
            severity_buckets[bucket] = severity_buckets.get(bucket, 0) + 1

        candidates = [by_value[value] for value in set(by_value)]

        stored = 0
        for start in range(0, len(candidates), ENRICH_BATCH_SIZE):
            chunk = candidates[start : start + ENRICH_BATCH_SIZE]

            enriched = await workflow.execute_activity(
                enrich_batch_activity,
                EnrichInput(tenant_id=payload.tenant_id, indicators=chunk),
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=DEFAULT_RETRY,
            )

            stored += await workflow.execute_activity(
                store_batch_activity,
                StoreInput(tenant_id=payload.tenant_id, indicators=enriched),
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=DEFAULT_RETRY,
                task_queue=rollup_queue(),
            )

        return IngestResult(
            run_id=run_id,
            tenant_id=payload.tenant_id,
            started_at=started_at,
            fetched=len(fetched),
            stored=stored,
            severity_buckets=severity_buckets,
        )
