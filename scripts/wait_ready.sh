#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"

timeout=${NIGHTJAR_WAIT_TIMEOUT:-900}

port_open() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

ready() { command -v uv >/dev/null 2>&1 && port_open 27017 && port_open 7233; }

if ! ready; then
  echo "waiting for the environment to finish setting up (up to ${timeout}s)..."
  deadline=$((SECONDS + timeout))
  while ! ready; do
    if [ "$SECONDS" -ge "$deadline" ]; then
      echo "environment is not ready: uv or the infrastructure containers are missing." >&2
      echo "run scripts/bootstrap.sh, then scripts/verify_env.sh. See docs/RUNBOOK.md." >&2
      exit 1
    fi
    sleep 2
  done
fi

exec "$@"
