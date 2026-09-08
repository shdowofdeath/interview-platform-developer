# Runbook

## Bring the stack up

```bash
docker compose up -d
```

Starts MongoDB (27017), a Temporal dev server (7233, UI on 8233) and an OTLP collector (4317). Wait for all three to report healthy:

```bash
docker compose ps
```

## Seed

```bash
cd services/ingest
uv sync --group dev
uv run python scripts/seed.py
```

Creates two tenants and their indicators. It prints a summary - note the counts, you will want them for comparison later. Re-running is safe; it drops and re-creates the collections.

## Run the service

Four processes. In CodeSandbox they start automatically; locally, four terminals:

```bash
# API
cd services/ingest && uv run uvicorn app:app --port 9400 --reload

# Temporal worker
cd services/ingest && uv run python worker.py

# Mock upstream (reputation vendor + feed publishers)
cd services/mock-upstream && uv run uvicorn app:app --port 9401
```

- OpenAPI: <http://localhost:9400/docs>
- Temporal UI: <http://localhost:8233>
- Collector: `docker compose logs -f otel-collector`

The worker logs every activity start and failure. Keep it visible; several failure modes never reach the HTTP response.

## Driving the system

```bash
# list indicators for a tenant
curl -s 'localhost:9400/api/v1/indicators?tenant_id=acme&limit=5' | jq

# per-tenant rollup (requires the X-Tenant-Id header)
curl -s -H 'X-Tenant-Id: acme' localhost:9400/api/v1/tenants/acme/rollup | jq

# start an ingest run
curl -s -X POST localhost:9400/api/v1/tenants/acme/ingest | jq

# re-enrich stale indicators
curl -s -X POST localhost:9400/api/v1/tenants/acme/sweep | jq

# import a STIX bundle directly
curl -s -X POST localhost:9400/api/v1/feeds/import \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"globex","feed_url":"http://localhost:9401/feeds/partner-bundle.json"}' | jq

# CVE applicability for an asset
curl -s 'localhost:9400/api/v1/cve/applicable?cpe=cpe:2.3:o:mikronet:routeros:6.47.3:*:*:*:*:*:*:*' | jq
```

## Looking at the data directly

```bash
docker compose exec mongo mongosh nightjar --quiet --eval '
  db.indicators.countDocuments({tenant_id: "acme"})
'
```

Useful counts when something looks off:

```javascript
db.indicators.countDocuments({tenant_id: "acme"})
db.indicators.countDocuments({tenant_id: "acme", "metadata.is_deleted": false})
db.indicators.countDocuments({tenant_id: "acme", last_enriched_at: null})
db.indicators.countDocuments({metadata: {$exists: false}})
```

## Common symptoms

### A workflow sits in RUNNING and never completes

Check the worker log, not the API response. A failing workflow *task* is retried indefinitely by Temporal, so the execution stays `RUNNING` and nothing surfaces to the caller. The worker log will be looping the same traceback.

The Temporal UI's event history for the execution shows the same thing under `WorkflowTaskFailed`.

### An activity fails and the workflow keeps retrying forever

Same cause, different layer. `maximum_attempts=0` means unlimited. Check the retry policy on the activity before assuming the activity is hanging.

### Enrichment returns nothing and the log shows 401s

The mock upstream suspends the API key after too many 429s in a short window, the same way the real vendor does. It recovers on its own after a few minutes.

### The reputation lookups all return instantly with identical data

The in-process TTL cache in `src/services/cache.py` is in front of the vendor. It is per-process, so restarting the worker clears it.

### `OverflowError: MongoDB can only handle up to 8-byte ints`

Known, NJ-3307. An indicator carrying a large X.509 serial. Currently takes the whole batch down.

### Collector receives fewer spans than you sent

Expected outside production. See `CLAUDE.md` on sampling.

## Resetting

```bash
docker compose down -v && docker compose up -d
cd services/ingest && uv run python scripts/seed.py
```

Drops the Mongo volume and the Temporal dev server's state.
