#!/bin/bash
VERSION=1.0.0

declare -A SERVICES
SERVICES=(
  ["auth-service"]="auth"
  ["book-service"]="book"
  ["inventory-service"]="inventory"
  ["order-service"]="order"
  ["notification-service"]="notification"
  ["api-gateway"]="gateway"
)

for s in "${!SERVICES[@]}"
do
  echo "Building $s..."
  docker build -t darko999/$s:$VERSION ./services/${SERVICES[$s]}
  docker push darko999/$s:$VERSION
done

# Frontend
docker build -t darko999/frontend:$VERSION ./frontend
docker push darko999/frontend:$VERSION
