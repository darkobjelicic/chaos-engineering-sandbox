#!/usr/bin/env bash
set -euo pipefail

EXPERIMENT="${1:-}"
EXPERIMENTS_DIR="chaos/experiments"
GRAFANA_URL="${GRAFANA_URL:-http://grafana.monitoring.local}"

usage() {
  echo "Usage: $0 <experiment-name>"
  echo ""
  echo "Available experiments:"
  for f in "$EXPERIMENTS_DIR"/*.yaml; do
    echo "  $(basename "$f" .yaml)"
  done
  exit 1
}

if [[ -z "$EXPERIMENT" ]]; then
  usage
fi

MANIFEST="$EXPERIMENTS_DIR/${EXPERIMENT}.yaml"
if [[ ! -f "$MANIFEST" ]]; then
  echo "Error: experiment '$EXPERIMENT' not found at $MANIFEST"
  usage
fi

annotate() {
  local text="$1"
  local tags="$2"
  curl -sf -X POST "$GRAFANA_URL/api/annotations" \
    -H "Content-Type: application/json" \
    -u "admin:admin" \
    -d "{\"text\": \"$text\", \"tags\": [\"chaos\", \"$tags\"]}" \
    > /dev/null 2>&1 || true
}

echo "[$(date '+%H:%M:%S')] Starting chaos experiment: $EXPERIMENT"

# Extract duration from manifest
DURATION=$(grep "duration:" "$MANIFEST" | tail -1 | awk '{print $2}' | tr -d '"')
echo "[$(date '+%H:%M:%S')] Duration: ${DURATION:-unknown}"

# Annotate start in Grafana
annotate "Chaos START: $EXPERIMENT" "$EXPERIMENT"

# Apply experiment
kubectl apply -f "$MANIFEST"
echo "[$(date '+%H:%M:%S')] Experiment applied. Watching..."

# Convert duration to seconds for sleep
SECONDS_WAIT=$(echo "$DURATION" | sed 's/m//' | awk '{print $1 * 60}' 2>/dev/null || echo 120)
sleep "$SECONDS_WAIT"

# Annotate end in Grafana
annotate "Chaos END: $EXPERIMENT" "$EXPERIMENT"

# Delete experiment (stops chaos)
kubectl delete -f "$MANIFEST"
echo "[$(date '+%H:%M:%S')] Experiment complete: $EXPERIMENT"
