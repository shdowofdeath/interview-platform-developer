from fastapi import APIRouter, HTTPException
from loguru import logger
from temporalio.client import Client
from temporalio.service import RPCError

from src.config import get_settings
from src.queues import enrichment_queue
from src.workflows.ingest_workflow import IngestInput, NightjarIngestWorkflow
from src.workflows.sweep_workflow import NightjarSweepWorkflow, SweepWorkflowInput

router = APIRouter(prefix="/api/v1", tags=["ingest"])

_client: Client | None = None


async def _temporal_client() -> Client:
    global _client
    if _client is None:
        settings = get_settings()
        _client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    return _client


@router.post("/tenants/{tenant_id}/ingest", status_code=202)
async def start_ingest(tenant_id: str, feed_urls: list[str] | None = None) -> dict[str, str]:
    client = await _temporal_client()
    workflow_id = f"ingest-{tenant_id}"

    try:
        handle = await client.start_workflow(
            NightjarIngestWorkflow.run,
            IngestInput(tenant_id=tenant_id, feed_urls=feed_urls or []),
            id=workflow_id,
            task_queue=enrichment_queue(),
        )
    except RPCError as exc:
        raise HTTPException(status_code=409, detail=f"ingest already running: {exc}") from exc

    logger.bind(tenant_id=tenant_id, workflow_id=workflow_id).info("started ingest workflow")
    return {"workflow_id": handle.id, "run_id": handle.result_run_id or ""}


@router.post("/tenants/{tenant_id}/sweep", status_code=202)
async def start_sweep(tenant_id: str) -> dict[str, str]:
    client = await _temporal_client()
    workflow_id = f"sweep-{tenant_id}"

    try:
        handle = await client.start_workflow(
            NightjarSweepWorkflow.run,
            SweepWorkflowInput(tenant_id=tenant_id),
            id=workflow_id,
            task_queue=enrichment_queue(),
        )
    except RPCError as exc:
        raise HTTPException(status_code=409, detail=f"sweep already running: {exc}") from exc

    logger.bind(tenant_id=tenant_id, workflow_id=workflow_id).info("started sweep workflow")
    return {"workflow_id": handle.id, "run_id": handle.result_run_id or ""}


@router.get("/tenants/{tenant_id}/ingest")
async def ingest_status(tenant_id: str) -> dict[str, str]:
    client = await _temporal_client()
    handle = client.get_workflow_handle(f"ingest-{tenant_id}")
    description = await handle.describe()
    return {
        "workflow_id": description.id,
        "status": description.status.name if description.status else "UNKNOWN",
        "task_queue": description.task_queue,
    }
