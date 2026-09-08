#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

CHART=deploy/helm/nightjar-ingest
APPS=deploy/argocd/apps
LIVE=deploy/live-state
RENDER_DIR=${NIGHTJAR_RENDER_DIR:-.render}

green() { printf '\033[32m%s\033[0m\n' "$1"; }
red() { printf '\033[31m%s\033[0m\n' "$1"; }

need() {
  local missing=0
  for binary in "$@"; do
    if ! command -v "$binary" >/dev/null 2>&1; then
      red "missing: $binary"
      missing=1
    fi
  done
  if [ "$missing" -eq 1 ]; then
    echo "install the missing tools, or rebuild the devcontainer. See docs/RUNBOOK.md." >&2
    exit 1
  fi
}

kubeconform_run() {
  if command -v kubeconform >/dev/null 2>&1; then
    kubeconform -strict -summary -
  else
    docker run --rm -i ghcr.io/yannh/kubeconform:latest -strict -summary -
  fi
}

app_names() {
  find "$APPS" -name '*.yaml' -exec basename {} .yaml \; | sort
}

render_app() {
  local app=$1
  local spec="$APPS/$app.yaml"
  local release
  local args=()

  release=$(yq -r '.metadata.name' "$spec")

  while read -r value_file; do
    [ -n "$value_file" ] || continue
    local resolved="$CHART/$value_file"
    if [ ! -f "$resolved" ]; then
      red "$app: valueFiles entry does not exist: $value_file"
      return 1
    fi
    args+=(-f "$resolved")
  done < <(yq -r '.spec.source.helm.valueFiles[]' "$spec")

  helm template "$release" "$CHART" \
    --namespace "$(yq -r '.spec.destination.namespace' "$spec")" \
    "${args[@]}"
}

stage_render() {
  need helm yq
  mkdir -p "$RENDER_DIR"

  for app in $(app_names); do
    echo "==> $app"
    yq -r '"    cluster:   " + .spec.destination.server,
           "    namespace: " + .spec.destination.namespace,
           "    revision:  " + .spec.source.targetRevision,
           "    values:    " + (.spec.source.helm.valueFiles | join(", "))' "$APPS/$app.yaml"

    render_app "$app" > "$RENDER_DIR/$app.yaml"

    echo "    objects:   $(grep -c '^kind:' "$RENDER_DIR/$app.yaml") in $(wc -l < "$RENDER_DIR/$app.yaml" | tr -d ' ') lines"
    kubeconform_run < "$RENDER_DIR/$app.yaml" | sed 's/^/    /'
  done

  green "rendered to $RENDER_DIR/ - nothing was deployed"
}

NORMALIZE='
  del(.status)
  | del(.metadata.uid)
  | del(.metadata.namespace)
  | del(.metadata.resourceVersion)
  | del(.metadata.creationTimestamp)
  | del(.metadata.generation)
  | del(.metadata.ownerReferences)
  | del(.metadata.annotations."kubectl.kubernetes.io/last-applied-configuration")
  | del(.metadata.annotations."deployment.kubernetes.io/revision")
  | del(.metadata.annotations | select(length == 0))
  | ... comments=""
'

stage_drift() {
  stage_render >/dev/null
  need yq

  local differs=0
  local live_only=0

  for environment in "$LIVE"/*; do
    [ -d "$environment" ] || continue
    local name rendered
    name=$(basename "$environment")
    rendered="$RENDER_DIR/nightjar-ingest-$name.yaml"

    echo "==> $name: captured live state vs the chart as $name's Application renders it"
    if [ ! -f "$rendered" ]; then
      red "    no rendered output for $name - is there an Application for it?"
      continue
    fi

    for live_file in "$environment"/*.yaml; do
      [ -f "$live_file" ] || continue
      local kind object
      kind=$(yq -r '.kind // ""' "$live_file")
      object=$(yq -r '.metadata.name // ""' "$live_file")
      [ -n "$kind" ] && [ -n "$object" ] || continue

      yq -r "select(.kind == \"$kind\" and .metadata.name == \"$object\") | $NORMALIZE" "$rendered" > /tmp/nightjar-want.$$
      yq -r "$NORMALIZE" "$live_file" > /tmp/nightjar-live.$$

      if [ ! -s /tmp/nightjar-want.$$ ]; then
        printf '    \033[33m%s\033[0m\n' "live only  $kind/$object - in the cluster, not in the chart"
        live_only=1
      elif diff -u /tmp/nightjar-want.$$ /tmp/nightjar-live.$$ > /tmp/nightjar-drift.$$; then
        echo "    matches    $kind/$object"
      else
        red "    differs    $kind/$object"
        sed -e '1,2d' -e 's/^/      /' /tmp/nightjar-drift.$$
        differs=1
      fi
    done
    command rm -f /tmp/nightjar-want.$$ /tmp/nightjar-live.$$ /tmp/nightjar-drift.$$
  done

  echo
  if [ "$differs" -eq 0 ] && [ "$live_only" -eq 0 ]; then
    green "the cluster holds exactly what the chart renders"
  else
    echo "Drift is not automatically wrong, and matching is not automatically right."
    echo "Work out which side is correct, and what each Application's syncPolicy will"
    echo "do about it on the next reconcile."
  fi
}

stage_plan() {
  need terraform

  echo "==> fmt"
  terraform -chdir=deploy/terraform fmt -check -diff

  echo "==> init"
  terraform -chdir=deploy/terraform init -input=false -backend=false >/dev/null

  echo "==> validate"
  terraform -chdir=deploy/terraform validate

  echo "==> plan"
  terraform -chdir=deploy/terraform init -input=false -reconfigure >/dev/null
  terraform -chdir=deploy/terraform plan -input=false -lock=false -no-color

  green "planned against a local state file and mock credentials - nothing was applied"
}

stage_lint() {
  need actionlint helm
  echo "==> workflows"
  actionlint || true
  echo "==> chart"
  helm lint "$CHART" --strict
}

stage_image() {
  need docker
  local tag=nightjar-ingest:local

  echo "==> build context"
  du -sh services/ingest

  echo "==> build"
  docker build -q -t "$tag" services/ingest

  echo "==> image"
  docker images "$tag" --format '    size {{.Size}}'
  docker run --rm "$tag" python -V | sed 's/^/    /'

  echo "==> config"
  docker inspect "$tag" --format '{{range .Config.Env}}    {{println .}}{{end}}'

  echo "==> layers"
  docker history "$tag" --no-trunc --format '    {{.Size}}  {{.CreatedBy}}' | cut -c1-160
}

usage() {
  cat <<'TXT'
usage: scripts/platform_check.sh [render|drift|plan|lint|image|all]

  render  render each ArgoCD Application exactly as it declares itself, and validate it
  drift   diff those renders against the captured live state in deploy/live-state/
  plan    terraform fmt, validate and plan, against mock credentials
  lint    actionlint on the workflows, helm lint on the chart
  image   build the container and inspect what ended up inside it
  all     all of the above

Nothing in here deploys anything. There is no cluster and no AWS account.
TXT
}

case "${1:-all}" in
  render) stage_render ;;
  drift) stage_drift ;;
  plan) stage_plan ;;
  lint) stage_lint ;;
  image) stage_image ;;
  all)
    stage_render
    echo
    stage_drift
    echo
    stage_plan
    echo
    stage_lint
    ;;
  *)
    usage
    exit 1
    ;;
esac
