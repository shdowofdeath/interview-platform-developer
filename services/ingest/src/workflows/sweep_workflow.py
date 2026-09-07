from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.activities.ingest_activities import SweepInput, SweepResult, sweep_stale_activity

SWEEP_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_attempts=3,
)


@dataclass
class SweepWorkflowInput:
    tenant_id: str


@workflow.defn(name="NightjarSweepWorkflow")
class NightjarSweepWorkflow:
    @workflow.run
    async def run(self, payload: SweepWorkflowInput) -> SweepResult:
        return await workflow.execute_activity(
            sweep_stale_activity,
            SweepInput(tenant_id=payload.tenant_id),
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(minutes=2),
            retry_policy=SWEEP_RETRY,
        )
