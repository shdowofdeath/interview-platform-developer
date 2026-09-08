# Globex onboarding - 2026-06-11

Not an incident. Kept here because the decisions made during onboarding are the reason the current deployment looks the way it does.

**Author**: Dana Feldstein
**Driving ticket**: NJ-2988

## What changed

Globex Logistics became the second tenant on the shared deployment. Until then Acme was the only customer and `tenant_id` was effectively decorative - every document in the collection belonged to the same customer, so a missing filter could not have produced a visible wrong answer.

From 2026-06-11 onwards, `tenant_id` is the only thing separating two customers' indicators in one collection.

## What we did before the cutover

- Confirmed every document had a `tenant_id` (backfilled 340 legacy documents that did not)
- Confirmed the API gateway injects `tenant_id` from the authenticated session
- Confirmed the retention job is tenant-scoped
- Asked Security for a pre-onboarding review. They asked for a written isolation audit, which we delivered in July (`docs/ai-notes/2026-07-14-tenancy-audit.md`)

## What we knowingly did not do

**Per-tenant databases or collections.** Rejected on operational cost. One collection, one index set, one retention job. This means isolation is a query-construction property rather than a structural one - every read path has to remember to filter, and nothing in the storage layer enforces it.

**Service-level enforcement of the tenant boundary.** The gateway is the trust boundary. We did not duplicate the check in the service. See `CLAUDE.md`.

**A cross-tenant read test in CI.** There is a unit test (`tests/test_tenancy.py`) but no integration test that seeds two tenants, calls the API as one of them, and asserts the response contains only their rows. This was on the list and did not get done before the cutover.

## Known consequence

Both tenants subscribe to overlapping community feeds. The same indicator legitimately appears for both, and the deduplication behaviour in that case has not been exercised at any volume. Worth watching.

## Follow-ups

- [x] Backfill `tenant_id` on legacy documents
- [x] Isolation audit (July)
- [ ] Cross-tenant integration test - NJ-3050, not started
- [ ] Load-test the shared-feed deduplication path - not started
