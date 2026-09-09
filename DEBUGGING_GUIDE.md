# Debugging Guide

Commands you will want during the session. Nothing here is a hint about what is wrong - it is the toolbox.

## Where output goes

| What | Where |
|---|---|
| HTTP request/response and API errors | the `uvicorn` terminal |
| Activity failures, workflow task failures, tracebacks | the `worker.py` terminal |
| Workflow event history, retry counts, stuck executions | Temporal UI, <http://localhost:8233> |
| Spans the service actually emitted | `docker compose logs -f otel-collector` |
| Upstream vendor behaviour, rate limiting, 429/401 | the `mock-upstream` terminal |

Every `curl` below runs in a terminal, where `localhost` is correct. To open the
Temporal UI or the MinIO console in a browser from a Codespace, take the link
from the **Ready check** terminal or the editor's **Ports** panel - the ports are
served on the codespace's own hostname, and a hand-built URL fails with a
certificate error.

A failing workflow *task* never reaches the HTTP caller. If a `POST` returns 202 and the workflow never finishes, the worker terminal is the only place the reason exists.

## Mongo

```bash
docker compose exec mongo mongosh nightjar --quiet --eval 'db.indicators.countDocuments({})'
```

Interactive shell:

```bash
docker compose exec mongo mongosh nightjar
```

Counts worth having side by side:

```javascript
db.indicators.countDocuments({tenant_id: "acme"})
db.indicators.countDocuments({tenant_id: "acme", "metadata.is_deleted": false})
db.indicators.countDocuments({tenant_id: "acme", last_enriched_at: null})
db.indicators.countDocuments({metadata: {$exists: false}})
db.indicators.distinct("tenant_id")
```

Explain a query the service runs:

```javascript
db.indicators.find({tenant_id: "acme", "metadata.is_deleted": false})
  .sort({first_seen: -1}).limit(50).explain("executionStats").executionStats
```

Indexes actually present:

```javascript
db.indicators.getIndexes()
```

Look at one document in full, including `raw_upstream`:

```javascript
db.indicators.findOne({value: "198.51.100.7"})
```

## API

```bash
# response size, which is often the thing you actually care about
curl -s 'localhost:9400/api/v1/indicators?tenant_id=acme&limit=50' | wc -c

# how many rows came back vs what total claims
curl -s 'localhost:9400/api/v1/indicators?tenant_id=acme&limit=50' \
  | jq '{returned: (.items | length), total: .total}'

# distinct tenants in a response
curl -s 'localhost:9400/api/v1/indicators?limit=200' \
  | jq -r '.items[].tenant_id' | sort | uniq -c

# walk every page and count distinct ids
for off in $(seq 0 50 1000); do
  curl -s "localhost:9400/api/v1/indicators?tenant_id=acme&limit=50&offset=$off" \
    | jq -r '.items[].id'
done | sort | uniq -c | awk '{print $1}' | sort | uniq -c
```

`:9400/docs` has every route with a live "try it" form.

## Temporal

```bash
# list executions
docker compose exec temporal temporal workflow list --namespace nightjar

# full event history for one execution
docker compose exec temporal temporal workflow show \
  --namespace nightjar --workflow-id sweep-acme

# what is registered on which queue
docker compose exec temporal temporal task-queue describe \
  --namespace nightjar --task-queue nightjar-ingest-dev
```

`task-queue describe` returning no pollers means nothing is listening on that queue.

## Traces

The collector is configured with a debug exporter, so every span it receives is printed:

```bash
docker compose logs --tail=200 otel-collector | grep -A20 'Span #'
```

Count what arrived:

```bash
docker compose logs otel-collector | grep -c 'Name           :'
```

If you send N requests and see fewer than N spans, that is a configuration question, not a broken pipeline.

## Mock upstream

```bash
# what the vendor is doing right now
curl -s localhost:9401/admin/state | jq

# a single lookup, unmediated by the cache
curl -s 'localhost:9401/v1/reputation?indicator=198.51.100.7&api_key=rep_live_7f4a2c9e1b8d6350a1f2' | jq
```

The vendor suspends the key after too many 429s in a window, same as the real one. It recovers by itself.

## Restarting cleanly

```bash
docker compose down -v && docker compose up -d
cd services/ingest && uv run python scripts/seed.py
```

The in-process reputation cache lives in the worker, so restarting `worker.py` clears it. Restarting the API does not.
