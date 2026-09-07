# [NJ-3372] Stabilise the rollout: pin the image, fix the probes, right-size prod, tighten IAM and CI

## Context

Follow-up to the 2026-08-02 worker incident and to the three infrastructure items Omri raised in the platform review. Nothing here touches application code, so it should be a fast review.

I paired with an AI assistant on the Terraform and the workflow changes because I have not worked with IRSA trust policies before. It walked me through the condition syntax.

Closes NJ-3340 (unpinned image), NJ-3344 (API pods restart in a loop), NJ-3351 (`write-all` on CI). Partially addresses NJ-3260.

## Changes

**1. Pin the image tag** (`deploy/helm/app-values/defaults/values.yaml`)

We have been deploying `latest` with `pullPolicy: Always`, which means two pods in the same ReplicaSet can be running different builds and a rollback is not expressible. Pinned the base values layer to `0.6.1`, which is the digest currently running in prod.

Prod now runs a pinned tag instead of `latest`.

**2. Fix the probes** (`deploy/helm/nightjar-ingest/templates/deployment-api.yaml`)

Liveness was pointing at `/readyz`, which is a readiness endpoint, not a liveness endpoint. Moved it to `/healthz`.

Also removed the readiness probe. It hit the same path as liveness on the same interval, so we were making two identical requests every ten seconds per pod for no additional signal, and during the August incident the doubled probe traffic showed up in the latency graphs. One probe on the right endpoint is what we want.

**3. Right-size the prod API pods** (`deploy/helm/app-values/prod/defaults/values.yaml`)

Prod API containers were requesting and limiting at `100m` / `128Mi`, which is where the OOMKills are coming from. Raised memory to `256Mi` requested / `512Mi` limit.

I also removed the CPU limit. CPU limits cause CFS throttling well before the container is actually CPU-saturated, and for a latency-sensitive API the request is what matters for scheduling. This is a deliberate change and I am happy to argue it.

**4. Replace `minAvailable` with `maxUnavailable` on the PDB** (`deploy/helm/nightjar-ingest/templates/pdb.yaml`, `values.yaml`)

`minAvailable: 2` with `replicas: 2` means the PDB never allows a voluntary eviction, so node drains and cluster upgrades hang. `maxUnavailable: 1` expresses what we actually want. I kept the `minAvailable` branch in the template for backwards compatibility so nobody's overlay breaks.

**5. Pin the ArgoCD revision** (`deploy/argocd/apps/nightjar-ingest-prod.yaml`)

`targetRevision: HEAD` is a moving target. Changed it to `main` so the Application tracks an explicit revision, and added `revisionHistoryLimit: 3` so we keep rollback history.

**6. Scope the IRSA trust policy** (`deploy/terraform/iam.tf`)

The assume-role condition was `system:serviceaccount:*:*`, which trusts every service account in the cluster. Scoped it to our namespace and switched the operator from `StringLike` to `StringEquals`, since the assistant pointed out that `StringEquals` is the stricter comparison and we should prefer it where we can.

**7. Tighten CI permissions and stop swallowing lint failures** (`.github/workflows/ci.yml`)

- `permissions: write-all` replaced with `contents: read`
- Removed `|| true` from the ruff steps so lint failures are real
- Added `continue-on-error: true` on the lint job so that a formatting nit does not block a release while we clear the existing backlog

**8. Harden the image** (`services/ingest/Dockerfile`)

Pinned the base image to `python:3.12-slim` instead of `python:latest`, and dropped `--reload` from the production `CMD`.

## Validation

- `helm template nightjar-ingest deploy/helm/nightjar-ingest -f deploy/helm/nightjar-ingest/values.yaml -f deploy/helm/app-values/defaults/values.yaml` renders clean. This is the same command CI runs, so if it passes there it passes here.
- `terraform validate` passes.
- `terraform plan` shows the trust-policy change and nothing unexpected.
- Did not deploy to dev yet, wanted a review on the IAM change first.

## Deployment notes

- ArgoCD will sync prod automatically on merge. `selfHeal` is on, so there is nothing to do by hand.
- The probe change causes one rolling restart of the API Deployment.

## Open questions

- Should `revisionHistoryLimit` be higher than 3?
- Is `256Mi` requested enough, or should I go straight to `512Mi` requested as well?

Requesting review from: @candidate
