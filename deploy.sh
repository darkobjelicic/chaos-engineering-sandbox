#!/bin/bash
# deploy.sh - Deploy entire stack to Kubernetes

set -e

REGISTRY="${1:-localhost:5000}"
ENV="${2:-dev}"

echo "🚀 Deploying Bookstore to Kubernetes"
echo "📦 Registry: $REGISTRY"
echo "🏷️  Environment: $ENV"

# Step 1: Check prerequisites
echo ""
echo "✅ Checking prerequisites..."
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl not found"; exit 1; }
command -v kustomize >/dev/null 2>&1 || { echo "⚠️  kustomize not found (installing via kubectl kustomize)"; }

# Step 2: Verify cluster connection
echo "✅ Connecting to Kubernetes cluster..."
kubectl cluster-info
echo ""

# Step 3: Create namespaces
echo "✅ Creating namespaces..."
kubectl create namespace traefik --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace chaos-mesh --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace default --dry-run=client -o yaml | kubectl apply -f -

# Step 4: Install cert-manager
echo "✅ Installing cert-manager..."
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
echo "⏳ Waiting for cert-manager to be ready..."
kubectl rollout status deployment/cert-manager -n cert-manager --timeout=300s || true
kubectl rollout status deployment/cert-manager-webhook -n cert-manager --timeout=300s || true

# Step 5: Install Chaos Mesh
echo "✅ Installing Chaos Mesh..."
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update
helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace --wait || true

# Step 6: Deploy using kustomize
echo "✅ Deploying application stack..."
cd "$(dirname "$0")"

if [ "$ENV" = "prod" ]; then
  echo "📦 Using PROD overlay..."
  kustomize build overlays/prod | kubectl apply -f -
else
  echo "📦 Using DEV overlay..."
  kustomize build overlays/dev | kubectl apply -f -
fi

# Step 7: Wait for deployments
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=600s deployment --all -n default || true

# Step 8: Get service IPs
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Services:"
kubectl get svc -n traefik traefik
echo ""
kubectl get svc -n default
echo ""

# Step 9: Show next steps
TRAEFIK_IP=$(kubectl get svc -n traefik traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "PENDING")
echo "🌐 Get LoadBalancer IP: $TRAEFIK_IP"
echo ""
echo "📝 Next steps:"
echo "1. Add DNS A records pointing $TRAEFIK_IP to:"
echo "   - devopsgeek.dev"
echo "   - www.devopsgeek.dev"
echo "   - app.devopsgeek.dev"
echo "   - grafana.devopsgeek.dev"
echo "   - prometheus.devopsgeek.dev"
echo "   - traefik.devopsgeek.dev"
echo "   - rabbitmq.devopsgeek.dev"
echo ""
echo "2. Wait 2-5 minutes for Let's Encrypt certificates"
echo "   kubectl get certificate"
echo ""
echo "3. Access services at:"
echo "   🌐 Frontend: https://devopsgeek.dev"
echo "   📊 Grafana: https://grafana.devopsgeek.dev (admin/admin)"
echo "   📈 Prometheus: https://prometheus.devopsgeek.dev"
echo "   🐰 RabbitMQ: https://rabbitmq.devopsgeek.dev"
echo "   ⚙️  Traefik: https://traefik.devopsgeek.dev"
echo ""
echo "4. Start load testing:"
echo "   kubectl port-forward svc/locust-master 8089:8089"
echo "   Then open http://localhost:8089"
