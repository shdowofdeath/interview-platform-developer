# Nightjar — Platform Engineering Challenge

**Role**: Platform Engineer, Cyber Security
**Format**: 90 minutes, live, screen shared
**AI**: allowed and encouraged. Use whatever you normally use.

---

## The situation

You have just joined the team that owns Nightjar. The engineer who built it left last week. There was no handover beyond the notes they left in `KNOWN_ISSUES.md`.

Nightjar is a multi-tenant threat-intelligence platform. Two customers are live on the same deployment: **Acme Manufacturing** (`acme`) and **Globex Logistics** (`globex`). Both feed indicators into the same collection, separated only by `tenant_id`.

This morning you have three things on your plate and 90 minutes. You will not finish all of them. That is expected and it is part of the design — **how you choose what to work on is being assessed as much as what you fix.**

---

## Before you start

Bring the stack up and seed it. `docs/RUNBOOK.md` has the commands. Roughly:

```bash
docker compose up -d
cd services/ingest && uv sync --group dev && uv run python scripts/seed.py
uv run uvicorn app:app --port 9400 --reload    # terminal 2
uv run python worker.py                        # terminal 3
cd ../mock-upstream && uv run uvicorn app:app --port 9401   # terminal 4
```

In CodeSandbox all of this starts automatically. OpenAPI is at `:9400/docs`, Temporal UI at `:8233`.

Keep the worker log visible. A lot of what you need to see only appears there.

---

## Mission 1 — Ticket NJ-3402, opened 06:12 today

> **Reporter**: Acme SOC lead, via the shared Slack channel
>
> "One of my analysts was reviewing our indicator list this morning and found an entry for a host we have never seen and that is not in our attack surface. She says the list also looks longer than the number our dashboard reports. Separately, an IP we escalated last week as a confirmed C2 has come back in our feed labelled benign with a confidence of 3. We did not change it. Can someone explain what we are looking at? We have a board review Thursday and I need to know whether our data is being mixed with someone else's."
>
> **Priority**: P1. Set by the account team, not by engineering.

This is the one that matters. Work out what is actually happening, decide what to do about it, and do as much of it as you can in the time you allocate.

You are not being graded on the number of lines you change. You are being graded on whether your explanation of the cause survives being poked at, and on whether your fix closes the hole rather than the symptom.

---

## Mission 2 — Ticket NJ-3277 is still open

The previous engineer's note says enrichment coverage plateaus at about 30% on large tenants and blames the vendor's rate limit. There is a support case open with the vendor and a review note in `docs/ai-notes/` that says not to spend time on the client code.

Coverage still is not moving.

Trigger a sweep and see for yourself:

```bash
curl -X POST localhost:9400/api/v1/tenants/acme/sweep
```

Then look at what the run actually reports, and at what changed in the database. Decide whether the previous engineer's diagnosis holds.

Note: the sweep path is layered. Fixing the first thing you find will expose the next one. Getting two layers deep here is a good result for the time available; getting one layer deep and explaining precisely what you would look for next is also a good result.

---

## Mission 3 — Review the open PR

`REVIEW_PR/` contains a pull request from a teammate, sent for your review. `PR_DESCRIPTION.md` is what they wrote, `REVIEW_PR.diff` is the change.

They wrote it with AI assistance and they are honest about that in the description. It is competently written, it closes three tickets off the board, and they need it merged before Thursday.

Leave a review. Approve it, request changes, or block it — and say why per change. If you would merge part of it and not the rest, say which part.

Be specific about severity. "This is a nit" and "this is a production incident waiting to happen" should not read the same in your review.

---

## Stretch — if you have time left

Pick whichever of these you find most interesting and say what you would do:

- **The platform layer.** Skim `.github/workflows/`, `services/ingest/Dockerfile` and `deploy/`. Name the three risks you would fix first and why in that order. You do not need to fix them.
- **A number that is wrong.** Somewhere in the API, a figure shown to customers does not mean what its name says it means. Find one, prove it with a query, and say what the correct definition should be.
- **Observability.** Send a request, then look at what the collector received. Tell us what you would change about what this service emits, in either direction.

---

## About the documentation in this repository

`CLAUDE.md`, `.cursorrules`, `AGENTS.md`, `docs/ai-notes/` and `KNOWN_ISSUES.md` are all part of the inherited codebase. They were written by people who worked on this system and believed what they wrote.

**Some of the claims in them are wrong.** Some are outdated, some were wrong when written, and at least one review note reaches a confident conclusion that the running code does not support. We are not going to tell you which.

This is deliberate, and it is the closest thing in this exercise to the actual job. Every real platform has a layer of documentation, ADRs and code comments asserting that something questionable was a considered decision. Some of those assertions are load-bearing and some are cover. Working out which is which — by reading the code and measuring the system rather than by trusting the prose — is the skill we are hiring for.

Your AI assistant will read those documents too, and it will tend to believe them. Watching how you handle that is part of the exercise.

---

## How we are assessing this

In rough order of weight:

1. **Whether your diagnosis is right**, and whether you can defend it when challenged. We will push back on at least one thing you are correct about, to see what happens.
2. **Whether you verified or assumed.** A claim backed by a query, a log line or a measurement counts for much more than a claim backed by plausible reasoning. This applies equally to claims your AI produced.
3. **Prioritisation.** Three missions, 90 minutes. Which you pick and what you consciously drop.
4. **Blast-radius thinking.** For a multi-tenant security platform, "does this fix leak data", "does this fix lose data" and "does this fix hide the problem" are different questions.
5. **How you use AI.** Delegating aggressively is good. Shipping something you cannot explain is not. We would rather see you catch your assistant being wrong than see you never need to.

## Rules

- Do not add dependencies without a one-line reason.
- Do not do a broad refactor. Small, defensible diffs.
- Narrate as you go. Silent thinking is hard for us to assess.
- If you find something that is not in any of the three missions, say so. Unplanned findings count for full credit.
- If you decide something is deliberately not worth fixing, say that explicitly. That is a valid and sometimes correct answer.

Good luck.
