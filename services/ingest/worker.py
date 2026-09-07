import asyncio

from loguru import logger
from temporalio.client import Client
from temporalio.worker import Worker

from src.activities.ingest_activities import (
    enrich_batch_activity,
    fetch_feed_activity,
    list_tenant_feeds_activity,
    store_batch_activity,
    sweep_stale_activity,
)
from src.config import get_settings
from src.db import init_db
from src.observability.logging import configure_logging
from src.observability.tracing import configure_tracing
from src.queues import enrichment_queue
from src.workflows.ingest_workflow import NightjarIngestWorkflow
from src.workflows.sweep_workflow import NightjarSweepWorkflow


async def main() -> None:
    configure_logging()
    configure_tracing()
    settings = get_settings()

    await init_db()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)

    queue = enrichment_queue()
    logger.bind(task_queue=queue, namespace=settings.temporal_namespace).info("nightjar worker starting")

    worker = Worker(
        client,
        task_queue=queue,
        workflows=[NightjarIngestWorkflow, NightjarSweepWorkflow],
        activities=[
            fetch_feed_activity,
            enrich_batch_activity,
            store_batch_activity,
            list_tenant_feeds_activity,
            sweep_stale_activity,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
