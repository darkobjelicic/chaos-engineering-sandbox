#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="chaos-sandbox"
KUBECONFIG_PATH="$HOME/.kube/config"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── 1. kind cluster ──────────────────────────────────────────────────────────
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

# ── 5. bookstore namespace + app ─────────────────────────────────────────────
log "Creating bookstore namespace..."
kubectl create namespace bookstore --dry-run=client -o yaml | kubectl apply -f -

log "Applying dev overlay..."
kubectl apply -k deploy/overlays/dev

log ""
log "✓ Cluster ready!"
log ""
log "ArgoCD UI:  kubectl port-forward svc/argocd-server -n argocd 8080:443"
log "ArgoCD password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
log ""
log "Add to /etc/hosts:"
log "  127.0.0.1  bookstore.local api.bookstore.local"
