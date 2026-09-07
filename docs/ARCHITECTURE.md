# Nightjar Architecture

## Services

### `services/ingest`

The only production service in this repo. One image, three roles selected at start:

| Entry point | Role |
|---|---|
| `app.py` | FastAPI HTTP API, port 9400 |
| `worker.py` | Temporal worker, polls the enrichment and rollup queues |
| `scripts/seed.py` | Local development seeder |

### `services/mock-upstream`

Local stand-in for two external systems: the commercial reputation vendor (`/v1/reputation`) and the feed publishers (`/feeds/*`). Port 9401. It reproduces the vendor's rate limiting, including the key suspension that follows too many 429s in a short window.

Not deployed. Local and CI only.

## Data flow

```
                        ┌──────────────────────────────────────────┐
                        │              Temporal                    │
                        │                                          │
  POST /ingest ────────>│  NightjarIngestWorkflow                  │
                        │    list_tenant_feeds_activity            │
                        │    fetch_feed_activity      (per feed)   │
                        │    enrich_batch_activity    (per chunk)  │
                        │    store_batch_activity     (rollup q)   │
                        │                                          │
  POST /sweep  ────────>│  NightjarSweepWorkflow                   │
                        │    sweep_stale_activity                  │
                        └───────────────┬──────────────────────────┘
                                        │
   feed publishers ─────────────────────┤
   reputation vendor ───────────────────┤
                                        v
                                    MongoDB
                                   indicators
                                    tenants
                                        │
   SOC dashboard <──── /api/v1 ─────────┘
```

Every span from both roles goes to the OTLP collector in `observability/`.

## Multi-tenancy

`tenant_id` is a string on every document, set from the request or the workflow input. There is no separate database or collection per tenant.

The trust boundary is the API gateway, which authenticates the caller and injects their `tenant_id`. The service trusts that value. See `CLAUDE.md` for the reasoning and `docs/ai-notes/2026-07-14-tenancy-audit.md` for the audit.

## Storage model

`Indicator` extends `BaseTenantDocument`, which carries `tenant_id` and a `DocumentMetadata` subdocument (`created_at`, `updated_at`, `is_deleted`, `deleted_at`).

**Deletes are soft.** Nothing in this service ever removes a document. The retention job sets `metadata.is_deleted = True`. Read paths are expected to filter on `metadata.is_deleted: False`.

Identity: `stix_id` is the natural key for feed-sourced indicators. `value` is not unique — the same IP can legitimately appear for two tenants.

## Enrichment

Two paths write enrichment:

- **Ingest** enriches in batches as indicators arrive, via `enrich_batch_activity`.
- **Sweep** re-enriches indicators that have gone stale (`stale_after_hours`, default 24), via `sweep_stale_activity`. This is the path that keeps confidence scores current.

Both call `ReputationClient.lookup`, which is fronted by an in-process TTL cache.

`confidence.aggregate` reduces the per-source scores in `source_confidence[]` to the single `confidence` integer that drives `severity` and the alert threshold (70).

## CVE applicability

`cpe_matcher` maps an asset CPE to the CVEs that apply to it, using the flattened dictionary in `data/seed/cpe_dictionary.json`. The dictionary is produced outside this repo by the vuln-intel team's flattening job, which expands NVD's wildcard and version-range match criteria into concrete CPE URIs.

## Task queues

`src/queues.py` is the only place queue names are constructed. Two queues:

- **enrichment** — the default queue, everything the workflow runs inline
- **rollup** — heavier store and aggregation work, on its own worker pool with different resource limits

Both are provisioned in `deploy/helm/nightjar-ingest/`.

## Observability

`src/observability/` wires a `TracerProvider` with a `BatchSpanProcessor` and an OTLP gRPC exporter, plus loguru configured for JSON output. Sampling is environment-dependent — see `CLAUDE.md`.

## Deployment

ArgoCD, app-of-apps. `deploy/argocd/` holds the `Application` manifests; `deploy/helm/` holds the chart and the per-environment values layers. Terraform in `deploy/terraform/` provisions the IAM role for the service account, the S3 bucket for feed archives and the KMS key.

Nothing is applied by hand.
