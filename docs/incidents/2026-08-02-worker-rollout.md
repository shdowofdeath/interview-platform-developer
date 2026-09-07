# INC-2026-08-02 — Ingest workflows stalled during worker rollout

**Severity**: SEV-3
**Duration**: 2026-08-02 09:14 → 2026-08-02 10:40
**Author**: Ravit Ozeri

## Impact

Eleven `NightjarIngestWorkflow` executions stopped advancing during a routine worker deployment. Customer-visible effect was delayed feed freshness for about 90 minutes. No data loss.

## Timeline

- **09:14** Worker deployment starts, rolling update, `maxUnavailable: 0`
- **09:21** Feed-freshness dashboard flatlines for both tenants
- **09:26** Paged. First check was the API, which reported all eleven executions as `RUNNING` with no error
- **09:38** Temporal UI shows repeated `WorkflowTaskFailed` events on every stalled execution
- **09:44** Worker logs are looping the same traceback
- **10:02** Old replicas finish draining
- **10:40** All eleven executions complete on their own. No intervention.

## Root cause

Determined to be task redelivery during the rollout. Both the old and the new replica set were polling the same task queue for roughly 90 seconds. Tasks picked up by a replica that had already received SIGTERM timed out and were redelivered.

## Contributing factors

1. **A failing workflow task is invisible to the caller.** The execution stays `RUNNING` and the API's status endpoint reports exactly that. Twelve of the twenty-four minutes to diagnosis went into looking at the wrong surface, because the HTTP layer looked healthy.

2. **`maximum_attempts=0` on the ingest retry policy.** Unlimited retries meant nothing ever surfaced as a terminal failure, which is the behaviour we want for feeds but which removes the signal we would otherwise have had.

3. **No alert on workflow-task failure rate.** We alert on workflow completion latency, not on task failures. The dashboard flatline was the only signal.

## Resolution

Raised `terminationGracePeriodSeconds` on the worker Deployment and made the worker stop polling on SIGTERM before exiting, so a terminating replica does not accept work it cannot finish.

## What is still open

The traceback in the worker log during the incident was not conclusively identified. Ravit's note at the time was that it looked like it came from inside the workflow body rather than from an activity, which would point at the workflow code rather than at the rollout. We reviewed the workflow for determinism hazards afterwards and found nothing that the SDK sandbox does not already handle — see `docs/ai-notes/2026-08-05-temporal-determinism-review.md`. The rollout explanation accounts for the timing, so we went with it.

If this recurs *outside* a deployment window, that conclusion is wrong and the workflow body is the place to look.

## Action items

- [x] `terminationGracePeriodSeconds` on the worker Deployment
- [x] Graceful shutdown on SIGTERM
- [x] Determinism review
- [ ] Alert on `WorkflowTaskFailed` rate — NJ-3260, not started
- [ ] Surface workflow-task failures on the status endpoint — not started
