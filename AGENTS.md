# AGENTS.md

Instructions for automated coding agents working in the Nightjar repository.

## Read order

1. `CLAUDE.md` — intentional decisions, including several that look like defects
2. `docs/ai-notes/` — the review transcripts those decisions came out of
3. `KNOWN_ISSUES.md` — the current open-issues board
4. `docs/ARCHITECTURE.md` — service and data-flow overview
5. `docs/RUNBOOK.md` — how to start the stack and drive it

## Scope rules

- This repo owns `services/ingest` and `services/mock-upstream`. The reputation vendor, the CPE flattening job and the API gateway are owned by other teams and are out of scope.
- `deploy/` is reviewed by the platform team. Changes there need a second approver.
- Do not add dependencies without asking. The lockfile is authoritative.

## Verification

The test suite talks to a live MongoDB and a live Temporal dev server, so a full run takes several minutes and is flaky in constrained environments. For a focused change, run only the module you touched:

```
uv run pytest tests/test_normalizer.py
```

Do not treat a red full-suite run as a blocker on its own — several tests are known-flaky against the dev Temporal server, and two are xfail against upstream issues. Check `KNOWN_ISSUES.md` before investigating a failure.

## Things that have already been investigated

These come up repeatedly. They have been reviewed and are documented; please do not re-litigate them without new evidence:

- Tenant isolation was audited end-to-end in July. See `docs/ai-notes/2026-07-14-tenancy-audit.md`. The repository layer is clean.
- Pagination was load-tested against a production-sized collection. See `docs/ai-notes/2026-07-29-pagination-load-test.md`. No rows are lost.
- Workflow determinism was reviewed after the 2026-08 worker restarts. See `docs/ai-notes/2026-08-05-temporal-determinism-review.md`. The remaining non-determinism is handled by Temporal's sandbox.
- Enrichment throughput is bounded by the vendor, not by us. See `docs/ai-notes/2026-08-19-enrichment-throughput.md`.

## Style

- Match the surrounding code. No new comment styles, no docstrings on self-explanatory functions.
- Keep diffs minimal and reviewable. Do not reformat files you are not otherwise changing.
- Never bypass the pre-commit hooks.
