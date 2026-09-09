#!/usr/bin/env bash
set -uo pipefail

cd "$(dirname "$0")/.."

export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"

timeout=${NIGHTJAR_WAIT_TIMEOUT:-900}

port_open() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

serving() { port_open 9400 && port_open 9401; }

if ! serving; then
  echo "waiting for the API and the mock upstream to start (up to ${timeout}s)..."
  deadline=$((SECONDS + timeout))
  while ! serving; do
    if [ "$SECONDS" -ge "$deadline" ]; then
      echo "the API or the mock upstream never came up. See docs/RUNBOOK.md." >&2
      exit 1
    fi
    sleep 2
  done
fi

scripts/verify_env.sh
failures=$?

cat <<'EOF'

  Start here      CHALLENGE.md - six stations, 90 minutes
  API             http://localhost:9400/docs
  Temporal        http://localhost:8233
  MinIO           http://localhost:9001    nightjar / nightjar-dev-secret

  The test suite and the linter are not green on arrival. You did not cause
  that, and you are not expected to get them green. Station 1 tells you which
  failures are yours.

EOF

exit "$failures"
