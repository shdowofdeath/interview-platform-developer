# Nightjar - Platform Engineering Challenge

**Role**: Platform Engineer, Cyber Security
**Format**: 90 minutes, live, screen shared
**AI**: allowed and encouraged. Use whatever you normally use.

---

## The situation

You have just joined the team that owns Nightjar, a multi-tenant
threat-intelligence platform. Two customers are live on the same deployment:
**Acme Manufacturing** (`acme`) and **Globex Logistics** (`globex`). Both feed
indicators into the same collection, separated only by `tenant_id`.

The engineer who built it left last week. There was no handover beyond the notes
in `KNOWN_ISSUES.md`.

Compliance has signed a commitment on your behalf: **from next month, every
tenant's live indicators must be written to object storage every night and
retained**, because customers' auditors need to see the snapshot a verdict was
derived from. You are shipping that this morning.

It is a small feature. It is also a feature that cannot exist without a bucket,
an IAM role, a config value, a ServiceAccount, a CronJob, and a place in the
sync path. That is the point.

---

## How this works

Six stations, one feature, ninety minutes.

| # | Station | Layer | ~mins |
| --- | --- | --- | --- |
| 1 | Build it | Python, Temporal, MongoDB | 15 |
| 2 | Provision it | Terraform | 12 |
| 3 | Package it | Helm | 18 |
| 4 | Ship it, on paper | ArgoCD | 10 |
| 5 | It is broken | infra-to-app debugging | 15 |
| 6 | Gate it | PR review | 10 |

**Your interviewer moves you between stations and will stop you at each
boundary, finished or not.** You are not expected to finish everything.
Unfinished stations are information, not failure. Narrate as you go - silent
thinking is hard for us to assess.

**Nothing you do today deploys anywhere.** There is no cluster and no AWS
account. Every station is proved with a local command, listed under `Done when`.

Some of the documentation in this repository is wrong. Working out which parts
is the exercise. See "About the documentation" at the bottom.

---

## Before you start

In a Codespace the stack starts itself. Locally, `docs/RUNBOOK.md` has the
commands; roughly:

```bash
scripts/bootstrap.sh                            # compose, tools, deps, seed
cd services/ingest && uv run uvicorn app:app --port 9400 --reload   # terminal 2
cd services/ingest && uv run python worker.py                       # terminal 3
cd services/mock-upstream && uv run uvicorn app:app --port 9401     # terminal 4
```

`scripts/verify_env.sh` tells you whether the stack is healthy. If anything in
it fails, say so rather than working around it.

OpenAPI `:9400/docs` · Temporal UI `:8233` · MinIO console `:9001`
(`nightjar` / `nightjar-dev-secret`).

In a Codespace those ports are only reachable on the codespace's own hostname,
not on `localhost`. The **Ready check** terminal prints the full links, and the
editor's **Ports** panel opens them too. Do not assemble the hostname yourself.
`localhost` is still correct inside a terminal, which is where every `curl` in
these docs runs.

Keep the worker log visible. A lot of what you need to see only appears there.

---

## Station 1 - Build it

**Goal**: the export exists and is correct.

- Add a Temporal activity that, for one tenant, writes every **live** indicator
  to object storage as JSONL, one object per line, at
  `<prefix>/<tenant_id>/<date>.jsonl`.
- Wire it into `SweepWorkflow` as a final step.
- The bucket and prefix come from config, not from a literal.

`services/ingest/tests/test_export.py` already exists and defines the contract.
Read it first - it tells you the names and shapes it expects.
`src/services/object_store.py` already has the S3 write.

**Files**: `services/ingest/src/activities/`, `src/workflows/sweep_workflow.py`,
`src/config.py`

**Done when**:

```bash
cd services/ingest && uv run pytest tests/test_export.py
docker compose exec minio mc ls --recursive local/nightjar-exports-dev/
```

The test passes, and your object is in the bucket.

---

## Station 2 - Provision it

**Goal**: the bucket and the permission to write to it exist in code.

Terraform runs against **mock credentials and a local state file**
(`deploy/terraform/mock_override.tf`). There is no AWS account and nothing you
run here reaches one.

- Add the export bucket. Versioned, encrypted, public access blocked.
- Give the service's role permission to write to that bucket, and only to it.

**Files**: `deploy/terraform/`

**Done when**:

```bash
scripts/platform_check.sh plan
```

`fmt`, `validate` and `plan` are clean and the plan contains your bucket.

Then tell me: **what else did you notice in that plan?**

---

## Station 3 - Package it

**Goal**: the export runs on a schedule, in both environments, with the right
bucket.

- Add the CronJob that runs the export nightly.
- Make the bucket name and prefix reach the container in **dev and in prod**.
- Check that the ServiceAccount the export runs as carries the role you scoped
  in Station 2. If Station 2 changed the role's name or who may assume it, this
  is where that lands.

**Files**: `deploy/helm/`

**Done when**:

```bash
scripts/platform_check.sh render
```

Your CronJob appears with the correct bucket for **dev** and for **prod**, and
the whole render passes `kubeconform -strict`.

Read that output carefully. It prints, per Application, which values files were
actually used.

---

## Station 4 - Ship it, on paper

**Goal**: you know what merging this does before you merge it.

Nothing here deploys. Answer from the repository, out loud, with evidence.

1. Which cluster and which namespace would each Application put this in?
2. Show me exactly what ArgoCD would sync, per environment.
3. You open a PR with everything from Stations 1 to 3. I approve it. **Walk me
   through what happens next, in order, until it is running in production.**

**Files**: `deploy/argocd/`, `.github/workflows/`

**Done when**: you have shown me the rendered manifests per Application and
answered question 3 out loud. If your answer to 3 changes your mind about
something you did in Stations 1 to 3, say so.

---

## Station 5 - It is broken

**Goal**: find out why, and why nobody knew.

Assume your export shipped to **dev** yesterday afternoon.

> The CronJob ran at 02:00. The Job completed. The pod exited 0. Every dashboard
> is green.
>
> The bucket is empty.

There is no cluster to poke. What you have is a hand-taken dump of the dev
environment in `deploy/live-state/dev/` - the CronJob, the Job, the pod, its
log, the ConfigMap, the ServiceAccount, the IAM policy, the bucket listing, the
events, and the ArgoCD Application status. Start with `deploy/live-state/dev/README.md`.

`scripts/platform_check.sh drift` diffs that dump against the rendered chart, if
that helps.

**Done when**: you can tell me why the bucket is empty, and why nothing alerted.

There is more than one thing wrong. Fixing the first would not have produced a
file.

---

## Station 6 - Gate it

**Goal**: a review you would actually leave.

`REVIEW_PR_PLATFORM/` is a pull request against this repository, opened by a
teammate who is honest in the description about having used AI. It touches Helm,
ArgoCD, Terraform, the CI workflow and the Dockerfile. `PR_DESCRIPTION.md` is
what they wrote; `REVIEW_PR.diff` is the change, and it applies cleanly to this
checkout if you would rather work in the files:

```bash
git apply --check REVIEW_PR_PLATFORM/REVIEW_PR.diff   # or: git apply
```

Approve, request changes, or block - and give me **the three comments you would
actually leave**, with severity. "This is a nit" and "this is a production
incident waiting to happen" should not read the same.

Two things reviewers usually skip:

- **Not everything in it is wrong.** If a change is correct but looks wrong, say
  so. Blocking a good change costs the team real time.
- **The description is not the artifact under review.** Diff the files.

---

## About the documentation in this repository

`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `docs/ai-notes/`, `KNOWN_ISSUES.md`
and `DEBUGGING_GUIDE.md` are part of the inherited codebase. They were written
by people who worked on this system and believed what they wrote.

**Some of the claims in them are wrong.** Some are outdated, some were wrong when
written, and at least one reaches a confident conclusion the running code does
not support. We are not going to tell you which.

This is deliberate, and it is the closest thing here to the actual job. Every
real platform has documentation and ADRs asserting that something questionable
was a considered decision. Some of those assertions are load-bearing and some
are cover. Telling them apart by reading the code and measuring the system,
rather than by trusting the prose, is the skill we are hiring for.

Your AI assistant will read those documents too, and it will tend to believe
them. How you handle that is part of the exercise.

---

## How we are assessing this

In rough order of weight:

1. **Whether you verified or assumed.** A claim backed by a command, a log line
   or a rendered manifest counts for far more than a claim backed by plausible
   reasoning. This applies equally to claims your assistant produced.
2. **Blast radius.** For a multi-tenant security platform, "does this leak
   data", "does this lose data" and "does this hide the problem" are three
   different questions. Station 4 is entirely this.
3. **Whether your diagnosis survives being poked at.** We will push back on at
   least one thing you are right about, to see what happens.
4. **How you use AI.** Delegating aggressively is good. Shipping something you
   cannot explain is not. We would rather watch you catch your assistant being
   wrong than watch you never need to.
5. **Whether the work is finishable by someone else.** Small, defensible diffs
   over broad refactors.

## Rules

- Do not add dependencies without a one-line reason.
- No broad refactors. Small diffs.
- If you find something outside the six stations, say so. Unplanned findings
  count for full credit.
- If you decide something is deliberately not worth fixing, say that explicitly.
  That is a valid and sometimes correct answer.
- If you run out of road on a station, say what you would do next. Describing
  the next step precisely scores close to taking it.

Good luck.
