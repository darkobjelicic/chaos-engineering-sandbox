#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="chaos-sandbox"
KUBECONFIG_PATH="$HOME/.kube/config"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── 1. kind cluster ──────────────────────────────────────────────────────────
# Promtail requires higher inotify limits — run once on host if Promtail crashes
# sudo sysctl fs.inotify.max_user_instances=512
# sudo sysctl fs.inotify.max_user_watches=524288

log "Creating kind cluster '$CLUSTER_NAME'..."
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  log "Cluster already exists, skipping creation."
else
  kind create cluster --name "$CLUSTER_NAME" --config kind-config.yaml
fi

kubectl cluster-info --context "kind-${CLUSTER_NAME}"

# ── 2. nginx ingress controller ──────────────────────────────────────────────
log "Installing nginx ingress controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

log "Waiting for ingress controller to be ready..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

# ── 3. ArgoCD ────────────────────────────────────────────────────────────────
log "Installing ArgoCD..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

log "Waiting for ArgoCD to be ready..."
kubectl wait --namespace argocd \
  --for=condition=available deployment/argocd-server \
  --timeout=180s

# ── 4. Sealed Secrets ────────────────────────────────────────────────────────
log "Installing Sealed Secrets controller..."
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml

# ── 5. Observability stack ───────────────────────────────────────────────────
log "Installing observability stack (monitoring namespace)..."
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values deploy/helm/kube-prometheus-stack/values-kind.yaml \
  --wait --timeout 5m

helm upgrade --install loki grafana/loki \
  --namespace monitoring \
  --values deploy/helm/loki/values-kind.yaml \
  --wait --timeout 3m

helm upgrade --install tempo grafana/tempo \
  --namespace monitoring \
  --values deploy/helm/tempo/values-kind.yaml \
  --wait --timeout 3m

helm upgrade --install promtail grafana/promtail \
  --namespace monitoring \
  --values deploy/helm/promtail/values-kind.yaml \
  --wait --timeout 2m

helm upgrade --install otelcol open-telemetry/opentelemetry-collector \
  --namespace monitoring \
  --values deploy/helm/otel-collector/values-kind.yaml \
  --wait --timeout 3m

# ── 6. Monitoring extras (ServiceMonitors + Grafana dashboards) ──────────────
log "Applying ServiceMonitors..."
kubectl apply -f deploy/monitoring/otel-collector-servicemonitor.yaml

log "Applying Grafana dashboards..."
kubectl apply -k deploy/grafana-dashboards

# ── 7. bookstore namespace + ArgoCD app ──────────────────────────────────────
log "Creating bookstore namespace..."
kubectl create namespace bookstore --dry-run=client -o yaml | kubectl apply -f -

log "Applying kind overlay..."
kubectl apply -k deploy/overlays/kind

log "Registering ArgoCD application..."
kubectl apply -f deploy/argocd/bookstore-app.yaml

log ""
log "✓ Cluster ready!"
log ""
log "ArgoCD UI:      kubectl port-forward svc/argocd-server -n argocd 8080:443"
log "ArgoCD pass:    kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
log "Grafana UI:     kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3001:80"
log "Grafana pass:   admin / admin"
log ""
log "Add to /etc/hosts:"
log "  127.0.0.1  bookstore.local api.bookstore.local"
