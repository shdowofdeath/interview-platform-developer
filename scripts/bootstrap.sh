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

stage_infra() {
  echo "==> infrastructure"
  docker compose up -d --wait
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
infra) stage_infra ;;
run) stage_run ;;
all)
  stage_deps
  stage_images
  stage_run
  cat <<'EOF'

Stack is up. Start the three processes (a Codespace starts them for you):

  cd services/ingest && uv run uvicorn app:app --port 9400 --reload
  cd services/ingest && uv run python worker.py
  cd services/mock-upstream && uv run uvicorn app:app --port 9401

OpenAPI :9400/docs   Temporal UI :8233
EOF
  ;;
*)
  echo "usage: $0 [deps|images|infra|run|all]" >&2
  exit 2
  ;;
esac
