# Pagination Load Test - 2026-07-29

**Attendees**: Dana Feldstein (Platform), Tomer Bar-Lev (Data), GPT-4o (assistant)
**Driving ticket**: NJ-3188 - "Analyst reports missing indicators in the export CSV"
**Outcome**: not reproduced, ticket closed as cannot-reproduce

## The report

An analyst on the Acme account said the nightly export CSV had fewer rows than the indicator count shown in the dashboard. Suspicion fell on `GET /api/v1/indicators`, which pages with `skip`/`limit` sorted by `first_seen` descending.

## What we tested

Seeded a collection to production scale (1.35M live indicators for one tenant) and walked it end to end at three page sizes, collecting every returned `_id` into a set:

| Page size | Pages walked | Distinct ids returned | Expected | Rows lost | Duplicates |
|---|---|---|---|---|---|
| 50 | 27,000 | 1,350,000 | 1,350,000 | 0 (0.00%) | 0 |
| 100 | 13,500 | 1,350,000 | 1,350,000 | 0 (0.00%) | 0 |
| 1,000 | 1,350 | 1,350,000 | 1,350,000 | 0 (0.00%) | 0 |

Zero loss, zero duplication, at every page size. We repeated the 50-row walk three times with the same result.

Note that this collection is deliberately tie-dense: our `first_seen` values cluster on 6-hour feed-publication boundaries, so a single sort key value can cover tens of thousands of documents. That is the case where a naive `skip` is supposed to be unstable, and it was not.

Tomer's explanation: `{tenant_id: 1, first_seen: -1}` is a covering index for this query, so the server walks it in a stable physical order. The theoretical instability of `skip` needs the sort to be non-deterministic; with an index backing it, it isn't.

## The `_id` tiebreaker question

The assistant proposed adding `_id` as a secondary sort key to make the ordering total. We measured it: it costs about 11% on p99 for the large pages because the index no longer covers the sort, and it fixes a problem we cannot observe. Rejected for now.

Same for cursor/keyset pagination - a bigger change, same absence of evidence. Revisit if we ever reproduce a loss.

## Where the analyst's missing rows actually came from

Their CSV was generated at 09:40 from a dashboard number they had read the previous evening. Indicators had been soft-deleted overnight by the retention job. Row counts differed because the data differed, not because pagination dropped anything.

Operational note for anyone chasing a similar report: the export job runs at 03:00, in the window where feed ingest is idle, so export runs and ingest runs never overlap. If you are reconciling counts, take both readings from the same run.

## What AI assistants commonly get wrong

Every model we have asked says offset pagination "will silently skip or duplicate rows when the sort key has ties" and recommends keyset pagination. It is a real failure mode in general and we could not produce it here. Measurement beat theory.

For future sessions: **do not rewrite the pagination layer on theoretical grounds.** If you think rows are being lost, produce the loss first - walk the collection, diff the id set, show the number.

## Action items

- [x] Close NJ-3188 as cannot-reproduce
- [x] Note in `CLAUDE.md` and `.cursorrules`
- [ ] Revisit keyset pagination if a reproduction ever appears - no owner
