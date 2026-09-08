# Nightjar

Multi-tenant threat-intelligence ingestion and enrichment platform.

Nightjar pulls indicators of compromise from STIX 2.1 feeds and a commercial reputation vendor, normalises them, enriches them with vendor confidence and CVE applicability, and serves them to per-customer SOC dashboards.

```
STIX feeds ──┐
             ├──> ingest (FastAPI + Temporal) ──> MongoDB ──> /api/v1 ──> SOC dashboards
vendor API ──┘                │
                              ├──> object storage (nightly compliance export)
                              └──> OTLP collector
```

## Repository layout

| Path | What it is |
|---|---|
| `services/ingest/` | The service: API, Temporal workflows and activities, repositories, domain logic |
| `services/mock-upstream/` | Stand-in for the reputation vendor and the feed publishers, for local runs |
| `data/seed/` | STIX bundles and a flattened CPE dictionary used by the seeder |
| `deploy/helm/` | Helm chart and the per-environment values layers |
| `deploy/argocd/` | The ArgoCD Applications that sync the chart |
| `deploy/terraform/` | Buckets, IRSA roles, secrets |
| `deploy/live-state/` | Hand-taken dumps of what is actually running, per environment |
| `observability/` | OTLP collector configuration |
| `docs/` | Architecture, runbook, incident write-ups, AI review notes |

## Getting started

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/shdowofdeath/interview-platform-developer)

In a Codespace, or any devcontainer, everything comes up on its own: dependencies, platform tooling, MongoDB, Temporal, MinIO, the collector, the seeded database, and the three processes. Anywhere with Docker:

```bash
scripts/bootstrap.sh      # tooling, dependencies, infrastructure, seed
scripts/verify_env.sh     # confirm the stack is healthy
```

The deployment layers are checked without a cluster and without an AWS account:

```bash
scripts/platform_check.sh render   # helm template per ArgoCD Application, then kubeconform
scripts/platform_check.sh drift    # that render vs deploy/live-state/
scripts/platform_check.sh plan     # terraform fmt, validate and plan, mock credentials
scripts/platform_check.sh lint     # actionlint, helm lint
scripts/platform_check.sh image    # build the container and inspect what is inside it
```

See [`docs/RUNBOOK.md`](docs/RUNBOOK.md) for the individual commands, and [`CLAUDE.md`](CLAUDE.md) for the conventions and the list of things that look like bugs but are not.

## If you are here for the interview

Read [`CHALLENGE.md`](CHALLENGE.md).
