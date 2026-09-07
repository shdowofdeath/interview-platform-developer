# Known Issues

Working notes from the previous owner of this service (left the team 2026-08-29). Not reviewed by anyone else. Triage state is whatever it was on their last day.

Ordered by when they were opened, not by severity.

---

## NJ-3301 — Severity column reads "low" for indicators analysts consider critical

**Status**: open · **Priority**: P2

Acme's SOC lead escalated three indicators that our dashboard shows as `low` and their own tooling shows as critical. Example: `198.51.100.7`, one of our sources scores it 95, we display severity `low`, and it never crosses the alert threshold of 70.

I think the vendor changed their scoring scale. Their docs used to say 0-100 and some responses now look like they are on a 0-10 basis, which would explain low aggregate numbers. Need to get confirmation from the vendor before touching anything.

Workaround given to Acme: use the per-source values in `source_confidence[]`.

---

## NJ-3305 — TLS verification disabled on the reputation client

**Status**: wontfix · **Priority**: P3

`verify=False` in `src/services/reputation_client.py`. This is a real MITM exposure on an egress path that carries customer indicator values.

Closed as wontfix per PLAT-114 — the corporate proxy's internal CA is not in the container trust store and Security signed off on the workaround. The actual fix is to bake the CA into the base image. That is an image-team task and nobody has picked it up.

I do not think this should have been closed. Reopening it needs someone more senior than me.

---

## NJ-3307 — `OverflowError` storing X.509 certificate serial numbers

**Status**: open · **Priority**: P1

Reproducible. Any indicator whose `raw_upstream` contains a certificate serial number larger than 2^63-1 fails the store activity:

```
OverflowError: MongoDB can only handle up to 8-byte ints
```

Serials are up to 20 bytes per RFC 5280, so this is not exotic — we see it whenever a feed includes cert observations. The API returns 500 and the whole batch is lost, not just the offending document.

Diagnosis is solid, I just did not have time for the fix. Options are to coerce oversized ints to strings before persisting, or to store `raw_upstream` as an opaque string. Needs a decision because it changes the shape of a field we expose to customers (NJ-2610).

---

## NJ-3309 — Webhook signature comparison is not constant-time

**Status**: open · **Priority**: P3

`src/services/webhook.py` compares the computed HMAC to the header with `==`. That is a timing side channel; it should be `hmac.compare_digest`. One-line fix, real issue, low exploitability given the signing key rotates weekly.

---

## NJ-3312 — Rollup totals do not match the indicator list

**Status**: open · **Priority**: P2

`GET /api/v1/tenants/{id}/rollup` reports a higher total than paging the list endpoint returns. For Acme it is off by about 4%. The gap is stable across runs, so it is not a race.

My read is that the dashboard caches the rollup for 15 minutes while the list endpoint is live, so the two readings are just taken at different times. Suggested to the frontend team that they drop the cache. Have not heard back.

---

## NJ-3318 — Indicators reported as stored never appear in the list endpoint

**Status**: open · **Priority**: P2

Feed import logs `upserted: 4` and the document count in Mongo goes up, but the new indicators do not show up in `GET /api/v1/indicators` for that tenant. Ever — not just for a while.

Probably an index build lagging behind the write. The compound index on `(tenant_id, first_seen)` was added late and the collection is large. `db.currentOp()` did not show a build in progress when I looked, but I only checked once.

Reproduce with the partner community feed on the globex tenant.

---

## NJ-3325 — CVE list looks short for MikroNet RouterOS assets

**Status**: open · **Priority**: P3

An analyst compared our applicability output for `MikroNet RouterOS 6.47.3` against the NVD web UI and we return fewer CVEs than they expected — 9 against their 13.

The CPE dictionary we consume is produced by the vuln-intel team's flattening job. If it has not been re-run since the last NVD sync it would be missing entries. Filed a request with them to re-flatten. Nothing to do on our side.

---

## NJ-3330 — Export path returns 500 for large tenants

**Status**: open · **Priority**: P2

`GET /api/v1/indicators?limit=10000` works locally but returns a gateway error in the deployed environments for the bigger tenants. Smaller tenants are fine, and the same tenant works at `limit=1000`.

Looks like a gateway timeout — the query does take a few seconds. Asked infra to raise the gateway read timeout for that route.

---

## NJ-3334 — Worker OOM from a Beanie document cache leak

**Status**: open · **Priority**: P1

The Temporal worker's RSS climbs steadily under sustained ingest and eventually gets OOM-killed by the kubelet — roughly every 40 hours at current volume. The curve is linear in documents processed, which points at documents being retained after the activity returns.

I believe Beanie's identity map holds every fetched document for the lifetime of the Motor client, and since our client is module-level it is never torn down. Tried `Document.get_settings().use_cache = False` and it did not help. Next step is a `tracemalloc` snapshot diff across a sweep.

This is the one I would pick up first if I were staying. It takes the worker down in production roughly twice a week.
