# dev live state - captured 2026-09-08T07:12Z

A dump of the dev environment, taken by hand after the nightly export failed to
produce anything. There is no cluster to poke, so this is all you get.

This is the state *after* the export change shipped, so it contains objects that
`deploy/helm/` on `main` does not have yet.

| File | What it is |
| --- | --- |
| `application-nightjar-ingest-dev-status.yaml` | `.status` of the ArgoCD Application |
| `cronjob-nightjar-ingest-export.yaml` | the nightly export CronJob |
| `job-nightjar-ingest-export-29813880.yaml` | last night's Job |
| `pod-nightjar-ingest-export-29813880-4qz8v.yaml` | that Job's pod |
| `pod.log` | that pod's container log, verbatim |
| `configmap-nightjar-ingest.yaml` | the config the container reads |
| `serviceaccount-nightjar-ingest.yaml` | the ServiceAccount it runs as |
| `deployment-nightjar-ingest.yaml` | the API Deployment |
| `iam-role-policy-nightjar-ingest-dev.json` | `aws iam get-role-policy` for the role in that annotation |
| `s3-buckets.txt` | `aws s3 ls`, and what is under the export prefix |
| `events.txt` | namespace events, controller log, rollout history |

The export change was reviewed and merged as-is. Its Helm change was this, in
full:

```
 deploy/helm/nightjar-ingest/values.yaml
 config:
+  exportBucket: nightjar-exports
+  exportPrefix: exports

 deploy/helm/app-values/defaults/values.yaml
 config:
+  exportBucket: nightjar-exports-dev
```

plus the CronJob template and the two lines in `templates/configmap.yaml` that
put `exportBucket` and `exportPrefix` into the ConfigMap.

`scripts/platform_check.sh drift` diffs this directory against the rendered
chart, if that is useful to you.
