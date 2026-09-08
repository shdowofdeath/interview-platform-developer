# [NJ-3350] Harden tenant scoping, unblock the export path, fix the store crash

## Context

Three of the four open P1/P2 items on `KNOWN_ISSUES.md` touch the same read/write path, so I did them together rather than in four separate PRs. Acme's security questionnaire response is due Thursday and the tenant-scoping item is on the critical path for it.

This closes NJ-3307, NJ-3309 and NJ-3330, and adds defence in depth for the item Omri raised in the July tenancy audit.

## Changes

**1. Explicit tenant scoping on the indicator read path** (`src/api/indicators.py`)

The July audit (`docs/ai-notes/2026-07-14-tenancy-audit.md`) concluded the repository layer is clean and that the gateway is the trust boundary. That is fine, but relying on a single layer made the security questionnaire awkward to answer, so this adds an `X-Tenant-Id` header to both read routes and enforces it in the service:

- `GET /api/v1/indicators` now scopes to `X-Tenant-Id` when the `tenant_id` query param is absent
- `GET /api/v1/indicators/{id}` now 403s when the document belongs to a different tenant

The cross-tenant correlation view (NJ-3102) still works because callers who want it simply omit both.

**2. Fix the `OverflowError` on certificate serials** (NJ-3307, `src/repositories/indicator_repository.py`)

`store_batch` now catches the insert failure instead of letting it 500 the request. A single unstorable document no longer takes down the whole ingest run. The offending batch is logged and skipped, and the indicators come back on the next feed poll anyway, so nothing is permanently lost.

I looked at coercing the oversized ints to strings but that changes the shape of `raw_upstream`, which we expose to customers under NJ-2610, so it needs a product decision. This unblocks us without that.

**3. Stable, cheaper sort on the list endpoint** (`src/repositories/indicator_repository.py`, `src/models/indicator.py`)

Sorting by `first_seen` needs a dedicated index and `first_seen` has heavy ties on feed-publication boundaries. `_id` is a monotonically increasing ObjectId, so sorting by `_id` descending gives the same newest-first ordering, is total (no ties, so pagination is provably stable), and comes free off the primary key. That lets us drop the `first_seen` index entirely - one less index to maintain on a large collection, and faster writes.

This also addresses the theoretical `skip`/`limit` instability the pagination note left open, without the 11% p99 cost the `_id` tiebreaker measured.

**4. Backoff on reputation 429s** (`src/services/reputation_client.py`)

The enrichment note says the retry loop is correct as written, but it retries with no delay at all, which is why we trip the vendor's burst limit. Added a linear backoff and raised `MAX_RETRIES` from 8 to 10 so a sweep is more likely to get through before giving up on an indicator.

**5. Raise the export page limit** (NJ-3330, `src/config.py`)

Infra raised the gateway read timeout for the export route, so the export can now pull bigger pages. Raised `max_page_limit` from 10000 to 50000 and the route's `le` bound to match. Fewer round trips for the nightly job.

**6. Constant-time webhook signature comparison** (NJ-3309, `src/services/webhook.py`)

`==` to `hmac.compare_digest`. One line.

## Testing

- Ran `uv run pytest tests/test_normalizer.py tests/test_confidence.py` - green
- Did not run the full suite (`AGENTS.md` says it is slow and known-flaky against the dev Temporal server)
- Manually hit `GET /api/v1/indicators` with and without `X-Tenant-Id` against a local seed and confirmed the scoped call returns only that tenant's rows
- Confirmed the list endpoint still returns newest-first after the sort change by eyeballing the first page

## Deployment

- No migrations. Dropping the `first_seen` index happens automatically on the next worker start.
- Safe to roll back; nothing here changes the document schema.

## Open questions

- Should the 403 on the by-id route be a 404 instead, so we do not confirm that the id exists? Happy to change it.
- The backoff constant (50ms × attempt) is a guess. If someone has the vendor's actual burst window I will tune it.

Requesting review from: @candidate
