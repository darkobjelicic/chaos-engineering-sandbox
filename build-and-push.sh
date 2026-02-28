#!/bin/bash
# build-and-push.sh - Build and push Docker images to registry

set -e

REGISTRY="${1:-localhost:5000}"
TAG="${2:-latest}"

echo "🐳 Building and pushing Docker images"
echo "📦 Registry: $REGISTRY"
echo "🏷️  Tag: $TAG"
echo ""

cd "$(dirname "$0")/FastAPI Application" || exit 1

# Build and push each service
services=(
  "services/auth"
  "services/book"
  "services/order"
  "services/inventory"
  "services/notification"
  "services/gateway"
  "frontend"
)

for service_path in "${services[@]}"; do
  service_name=$(basename "$service_path")
  
  echo "🔨 Building $service_name..."
  docker build -t "$REGISTRY/$service_name:$TAG" "$service_path"
  
  echo "📤 Pushing $service_name:$TAG to $REGISTRY..."
  docker push "$REGISTRY/$service_name:$TAG"
  
  echo "✅ $service_name:$TAG pushed successfully"
  echo ""
done

echo "🎉 All images built and pushed!"
echo ""
echo "💡 Tip: Update k8s deployments with:"
echo "   sed -i 's|localhost:5000|$REGISTRY|g' k8s/base/*/deployment.yaml"
