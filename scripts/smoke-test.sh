#!/bin/sh
set -eu

API_URL="${API_URL:-http://localhost:8080}"
WEB_URL="${WEB_URL:-http://localhost:3000}"

curl -fsS "$API_URL/healthz" >/dev/null
curl -fsS "$API_URL/api/v1/incidents?limit=1" >/dev/null
curl -fsS "$API_URL/api/v1/resources" >/dev/null
curl -fsS "$API_URL/api/v1/summary" >/dev/null
curl -fsS "$WEB_URL" | grep -q "CRISIS"

echo "CrisisMesh smoke test passed"

