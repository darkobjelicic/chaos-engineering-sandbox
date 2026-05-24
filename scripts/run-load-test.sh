#!/usr/bin/env bash
set -euo pipefail

SCRIPT="${1:-load-testing/k6/scripts/load.js}"

# Port-forward Prometheus for k6 remote write
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090 &
PF_PID=$!
trap "kill $PF_PID 2>/dev/null" EXIT
sleep 2

echo "[$(date '+%H:%M:%S')] Starting load test: $SCRIPT"
echo "[$(date '+%H:%M:%S')] Metrics → Prometheus (localhost:9090)"
echo "[$(date '+%H:%M:%S')] Baseline: 8 min | Chaos window: 15 min"
echo ""

K6_PROMETHEUS_RW_SERVER_URL=http://localhost:9090/api/v1/write \
  k6 run --out experimental-prometheus-rw \
  --env BASE_URL="${BASE_URL:-http://api.bookstore.local}" \
  "$SCRIPT"
