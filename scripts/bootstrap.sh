#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export PATH="$HOME/.local/bin:$PATH"

ensure_uv() {
  command -v uv >/dev/null 2>&1 && return
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  # terminals and tasks started later do not inherit this shell's PATH
  if [ ! -x /usr/local/bin/uv ]; then
    ln -sf "$(command -v uv)" /usr/local/bin/uv 2>/dev/null ||
      sudo ln -sf "$(command -v uv)" /usr/local/bin/uv 2>/dev/null || true
  fi
}

stage_deps() {
  echo "==> uv"
  ensure_uv
  uv --version
  echo "==> dependencies"
  uv sync --group dev --directory services/ingest
  uv sync --directory services/mock-upstream
}

stage_images() {
  echo "==> container images"
  docker compose pull --quiet
}

KUBECONFORM_VERSION=0.7.0
ACTIONLINT_VERSION=1.7.7
YQ_VERSION=4.53.2

work_dir=
# a RETURN trap fires again when the calling stage returns, by which point work_dir is gone
trap 'if [ -n "$work_dir" ]; then command rm -rf "$work_dir"; fi' EXIT

platform_pair() {
  local os arch
  case "$(uname -s)" in
  Linux) os=linux ;;
  Darwin) os=darwin ;;
  *)
    echo "unsupported OS: $(uname -s)" >&2
    return 1
    ;;
  esac
  case "$(uname -m)" in
  x86_64 | amd64) arch=amd64 ;;
  aarch64 | arm64) arch=arm64 ;;
  *)
    echo "unsupported architecture: $(uname -m)" >&2
    return 1
    ;;
  esac
  echo "$os $arch"
}

install_bin() {
  local name=$1 source=$2
  chmod +x "$source"
  if [ -w /usr/local/bin ]; then
    mv -f "$source" "/usr/local/bin/$name"
  elif sudo -n true 2>/dev/null; then
    sudo mv -f "$source" "/usr/local/bin/$name"
  else
    mkdir -p "$HOME/.local/bin"
    mv -f "$source" "$HOME/.local/bin/$name"
  fi
}

# `cmd | head -1` dies of SIGPIPE, and so exits 141 under pipefail, when the writer
# is still going after head has closed the pipe - terraform prints a second line and
# then an out-of-date notice once its checkpoint call returns
version_line() {
  local output
  output=$("$@" 2>&1)
  printf '%s\n' "${output%%$'\n'*}"
}

stage_tools() {
  read -r os arch <<<"$(platform_pair)"
  work_dir=$(mktemp -d)

  echo "==> platform tooling ($os/$arch)"

  if ! command -v kubeconform >/dev/null 2>&1; then
    curl -fsSL "https://github.com/yannh/kubeconform/releases/download/v${KUBECONFORM_VERSION}/kubeconform-${os}-${arch}.tar.gz" |
      tar -xz -C "$work_dir" kubeconform
    install_bin kubeconform "$work_dir/kubeconform"
  fi
  kubeconform -v

  if ! command -v actionlint >/dev/null 2>&1; then
    curl -fsSL "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_${os}_${arch}.tar.gz" |
      tar -xz -C "$work_dir" actionlint
    install_bin actionlint "$work_dir/actionlint"
  fi
  version_line actionlint --version

  if ! command -v yq >/dev/null 2>&1; then
    curl -fsSL "https://github.com/mikefarah/yq/releases/download/v${YQ_VERSION}/yq_${os}_${arch}" -o "$work_dir/yq"
    install_bin yq "$work_dir/yq"
  fi
  yq --version

  for binary in helm terraform; do
    if command -v "$binary" >/dev/null 2>&1; then
      version_line "$binary" version
    else
      echo "missing: $binary - see docs/RUNBOOK.md"
    fi
  done

  # cached here so the first terraform plan of the session does not wait on a provider download
  if command -v terraform >/dev/null 2>&1; then
    echo "==> terraform provider cache"
    terraform -chdir=deploy/terraform init -input=false >/dev/null
    terraform -chdir=deploy/terraform providers | sed 's/^/    /'
  fi
}

stage_prebuild() {
  stage_images
  stage_tools
}

stage_infra() {
  echo "==> infrastructure"
  docker compose up -d
  # `--wait` counts minio-init's clean exit as a failure, so the bucket job is gated on its own
  docker compose wait minio-init >/dev/null
  docker compose up -d --wait --no-recreate mongo temporal minio otel-collector
  docker compose ps
}

stage_run() {
  stage_infra
  echo "==> seed"
  (cd services/ingest && uv run python scripts/seed.py)
}

case "${1:-all}" in
deps) stage_deps ;;
images) stage_images ;;
tools) stage_tools ;;
prebuild) stage_prebuild ;;
infra) stage_infra ;;
run) stage_run ;;
all)
  stage_deps
  stage_prebuild
  stage_run
  cat <<'EOF'

Stack is up. Start the three processes (a Codespace starts them for you):

  cd services/ingest && uv run uvicorn app:app --port 9400 --reload
  cd services/ingest && uv run python worker.py
  cd services/mock-upstream && uv run uvicorn app:app --port 9401

OpenAPI :9400/docs   Temporal UI :8233   MinIO console :9001

Platform stations need no cluster and no AWS account:

  scripts/platform_check.sh render|drift|plan|lint|image
EOF
  ;;
*)
  echo "usage: $0 [deps|images|tools|prebuild|infra|run|all]" >&2
  exit 2
  ;;
esac
