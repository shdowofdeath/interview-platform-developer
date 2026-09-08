#!/usr/bin/env bash
set -uo pipefail

cd "$(dirname "$0")/.."

export PATH="$HOME/.local/bin:$PATH"

failures=0

check() {
  local label="$1" snippet="$2"
  if output=$(bash -c "$snippet" 2>&1); then
    printf 'PASS  %-24s %s\n' "$label" "$(echo "$output" | tail -1)"
  else
    printf 'FAIL  %-24s %s\n' "$label" "$(echo "$output" | tail -1)"
    failures=$((failures + 1))
  fi
}

http_code() {
  echo "c=\$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 $1); echo \"HTTP \$c\"; [ \"\$c\" = 200 ]"
}

# counted through the service's own settings, so a stray MongoDB on 27017 shows up as a failure here
counts=$(uv run --directory services/ingest python - <<'PY' 2>/dev/null
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

from src.config import get_settings


async def main() -> None:
    settings = get_settings()
    db = AsyncIOMotorClient(settings.mongo_url)[settings.mongo_database]
    print(await db.tenants.count_documents({}), await db.indicators.count_documents({}))


asyncio.run(main())
PY
)
tenants=${counts%% *}
indicators=${counts##* }

echo "Nightjar environment check"
echo

check "docker" "docker version --format '{{.Server.Version}}'"
check "uv" "uv --version"

check "tool: helm" "helm version --short"
check "tool: kubeconform" "kubeconform -v"
check "tool: terraform" "terraform version | head -1"
check "tool: actionlint" "actionlint --version | head -1"
check "tool: yq" "yq --version"

for svc in mongo temporal otel-collector minio; do
  check "compose: $svc" "docker compose ps --status running --services | grep -qx $svc && echo running"
done

check "minio: bucket" "docker compose exec -T minio mc ls local/nightjar-exports-dev >/dev/null && echo nightjar-exports-dev"

check "db: tenants" "echo '${tenants:-0} tenants'; [ '${tenants:-0}' = 2 ]"
check "db: indicators" "echo '${indicators:-0} indicators'; [ '${indicators:-0}' -ge 4000 ]"
check "cpe dictionary" "[ -s data/seed/cpe_dictionary.json ] && echo present"
check "temporal: namespace" "docker compose exec -T temporal temporal operator namespace describe --address 127.0.0.1:7233 nightjar >/dev/null && echo nightjar"
check "temporal ui" "$(http_code localhost:8233)"
check "api: /healthz" "$(http_code localhost:9400/healthz)"
check "api: /docs" "$(http_code localhost:9400/docs)"
check "api: indicators" "curl -s --max-time 5 'localhost:9400/api/v1/indicators?tenant_id=acme&limit=1' | grep -qE '\"items\":\[\{' && echo responded"
check "mock upstream" "$(http_code localhost:9401/)"
check "worker process" "pgrep -f worker.py >/dev/null && echo running"

check "platform: render" "scripts/platform_check.sh render >/dev/null && echo 2 applications"
check "platform: providers" "[ -d deploy/terraform/.terraform/providers ] && echo cached"

echo
if [ "$failures" -eq 0 ]; then
  echo "Ready. Compare the seed counts against the baseline in the interviewer pack before you start."
else
  echo "$failures check(s) failed. Run scripts/bootstrap.sh, then re-run this."
fi
exit "$failures"
