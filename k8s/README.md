# 🚀 Kubernetes Deployment - Bookstore Chaos Engineering Setup

Complete K8s manifests za bookstore aplikaciju sa **Traefik ingress**, **automatic HTTPS via cert-manager**, **Prometheus + Grafana monitoring**, **Chaos Mesh**, i **Locust load testing**.

## 📋 Prerequisites

- Kubernetes cluster (v1.20+) - `kubectl` configured
- `kustomize` CLI (ili `kubectl kustomize`)
- Valid domain (devopsgeek.dev) - DNS pointed to LoadBalancer IP
- 8GB RAM minimum na cluster-u
- cert-manager instaliran: 
  ```bash
  kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
  ```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  KUBERNETES CLUSTER                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │ TRAEFIK INGRESS (LoadBalancer Service)             │  │
│  │ - Automatic HTTPS with Let's Encrypt               │  │
│  │ - Routes: app.devopsgeek.dev, grafana., etc.      │  │
│  └────────────────────────────────────────────────────┘  │
│                           ↓                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ MICROSERVICES (Auth, Book, Order, Inventory, etc.) │  │
│  │ - 2 replicas each (rolling updates)                │  │
│  │ - Pod anti-affinity (spread across nodes)          │  │
│  │ - Health checks (liveness + readiness)             │  │
│  └────────────────────────────────────────────────────┘  │
│                           ↓                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ DATA LAYER (Postgres + RabbitMQ)                   │  │
│  │ - StatefulSets with PVCs                           │  │
│  │ - 4 separate databases (auth, book, inventory, order) │
│  │ - RabbitMQ management UI exposed                   │  │
│  └────────────────────────────────────────────────────┘  │
│                           ↓                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ MONITORING (Prometheus + Grafana)                  │  │
│  │ - Scrapes Traefik metrics                          │  │
│  │ - Collects pod/node stats                          │  │
│  │ - Available at: grafana.devopsgeek.dev             │  │
│  └────────────────────────────────────────────────────┘  │
│                           ↓                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ CHAOS MESH (Automated Chaos Experiments)           │  │
│  │ - Pod kills, network delays, packet loss           │  │
│  │ - CPU stress, pod failures                         │  │
│  │ - Scheduled via cron                               │  │
│  └────────────────────────────────────────────────────┘  │
│                           ↓                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ LOCUST (Load Testing)                              │  │
│  │ - Master-worker architecture                       │  │
│  │ - Simulates concurrent users                       │  │
│  │ - Web UI on locust-master service                  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## 📦 Folder Structure

```
k8s/
├── base/                           # Core components
│   ├── namespace.yaml              # default namespace
│   ├── postgres/                   # 4x PostgreSQL DBs
│   ├── rabbitmq/                   # Message queue
│   ├── auth-service/               # Auth microservice
│   ├── book-service/               # Book catalog service
│   ├── order-service/              # Order processing
│   ├── inventory-service/          # Inventory management
│   ├── notification-service/       # Event notifications
│   ├── gateway/                    # API Gateway
│   └── frontend/                   # React frontend
├── traefik/                        # Ingress controller
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingressroutes.yaml          # Main app routes
│   └── monitoring-ingressroutes.yaml
├── cert-manager/                   # HTTPS certificates
│   └── issuer.yaml                 # Let's Encrypt issuers
├── monitoring/                     # Prometheus + Grafana
│   └── deployment.yaml
├── chaos-mesh/                     # Chaos experiments
│   └── experiments.yaml            # Pod kill, network delays, etc.
├── locust/                         # Load testing
│   ├── locustfile.py              # Test scenarios
│   └── deployment.yaml
├── overlays/                       # Kustomize overlays
│   ├── dev/                        # Dev environment
│   └── prod/                       # Prod environment
├── kustomization.yaml              # Root kustomization
└── README.md                       # This file
```

## 🌐 DNS Records Required

Add these DNS records to `devopsgeek.dev`:

```
A  devopsgeek.dev              -> <LoadBalancer IP>
A  www.devopsgeek.dev          -> <LoadBalancer IP>
A  app.devopsgeek.dev          -> <LoadBalancer IP>
A  grafana.devopsgeek.dev      -> <LoadBalancer IP>
A  prometheus.devopsgeek.dev   -> <LoadBalancer IP>
A  traefik.devopsgeek.dev      -> <LoadBalancer IP>
A  rabbitmq.devopsgeek.dev     -> <LoadBalancer IP>
```

Get LoadBalancer IP:
```bash
kubectl get svc -n traefik traefik
# Copy EXTERNAL-IP and create A records
```

## 🚀 Deployment Steps

### 1. Setup Prerequisites

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Verify cert-manager is ready
kubectl rollout status deployment/cert-manager -n cert-manager
kubectl rollout status deployment/cert-manager-webhook -n cert-manager

# Install Chaos Mesh (optional, but recommended)
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace

# Verify Chaos Mesh is ready
kubectl rollout status deployment/chaos-mesh-controller-manager -n chaos-mesh
```

### 2. Configure Docker Registry (on your local machine)

Before deploying, build and push images to a registry. You have options:

#### Option A: Local Registry in Cluster
```bash
# Install Docker registry in cluster
kubectl create namespace docker-registry
helm install docker-registry twun/docker-registry -n docker-registry

# Port-forward to push images
kubectl port-forward -n docker-registry svc/docker-registry 5000:5000 &

# Build and push (from local machine)
cd FastAPI\ Application/

docker build -t localhost:5000/auth-service:latest ./services/auth/
docker build -t localhost:5000/book-service:latest ./services/book/
docker build -t localhost:5000/order-service:latest ./services/order/
docker build -t localhost:5000/inventory-service:latest ./services/inventory/
docker build -t localhost:5000/notification-service:latest ./services/notification/
docker build -t localhost:5000/api-gateway:latest ./services/gateway/
docker build -t localhost:5000/frontend:latest ./frontend/

docker push localhost:5000/auth-service:latest
docker push localhost:5000/book-service:latest
docker push localhost:5000/order-service:latest
docker push localhost:5000/inventory-service:latest
docker push localhost:5000/notification-service:latest
docker push localhost:5000/api-gateway:latest
docker push localhost:5000/frontend:latest
```

#### Option B: Docker Hub
```bash
# Build with your Docker Hub username
docker build -t <your-docker-username>/auth-service:latest ./services/auth/
docker push <your-docker-username>/auth-service:latest

# Then update image references in k8s/base/*/deployment.yaml
```

### 3. Deploy to Cluster

```bash
# Option 1: Using kustomize (recommended)
cd k8s/
kustomize build . | kubectl apply -f -

# Option 2: Direct kubectl apply
kubectl apply -f traefik/
kubectl apply -f cert-manager/
kubectl apply -f base/
kubectl apply -f monitoring/
kubectl apply -f locust/
kubectl apply -f chaos-mesh/

# Option 3: Using overlays (dev/prod)
kustomize build overlays/prod | kubectl apply -f -
```

### 4. Verify Deployment

```bash
# Check all pods are running
kubectl get pods

# Check services
kubectl get svc

# Check ingress routes
kubectl get ingressroutes

# Check traefik loadbalancer external IP
kubectl get svc -n traefik traefik

# Follow logs
kubectl logs -f deploy/auth-service
kubectl logs -f deploy/api-gateway
```

### 5. Access Services

Once DNS is configured and pods are ready:

- **Frontend (App)**: https://devopsgeek.dev or https://www.devopsgeek.dev
- **API Gateway**: https://app.devopsgeek.dev
- **Grafana (Monitoring)**: https://grafana.devopsgeek.dev (admin/admin)
- **Prometheus**: https://prometheus.devopsgeek.dev
- **RabbitMQ Management**: https://rabbitmq.devopsgeek.dev
- **Traefik Dashboard**: https://traefik.devopsgeek.dev

## 🧪 Chaos Engineering Tests

### Run Locust Load Test

```bash
# Port-forward to locust web UI
kubectl port-forward svc/locust-master 8089:8089

# Open browser: http://localhost:8089
# Set number of users (e.g., 100) and spawn rate (e.g., 10/sec)
# Click "Start swarming"
```

### Monitor Chaos Mesh Experiments

```bash
# View running experiments
kubectl get podchaos
kubectl get networkchaos
kubectl get stresschaos

# Check experiment status
kubectl describe podchaos kill-order-service-pod

# View experiments in action (Grafana)
# https://grafana.devopsgeek.dev -> Create dashboard -> Add panels for:
#   - Request latency changes
#   - Error rate spikes
#   - Pod restarts
#   - Network latency
```

### Manual Chaos Experiment Example

```bash
# Kill a pod manually
kubectl delete pod -l app=order-service

# Add network delay to order→inventory communication
kubectl apply -f - <<EOF
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: manual-order-delay
  namespace: default
spec:
  action: delay
  mode: all
  duration: "2m"
  delay:
    latency: "1s"
    jitter: "200ms"
  target:
    namespace: default
    selector:
      app: inventory-service
  source:
    namespace: default
    selector:
      app: order-service
EOF

# Watch impact in Grafana while Locust is running
# Then delete the chaos experiment
kubectl delete networkchaos manual-order-delay
```

## 📊 Monitoring & Dashboards

### Grafana Setup

1. Login: https://grafana.devopsgeek.dev (admin/admin)
2. Add Prometheus data source:
   - Settings → Data Sources → Add Prometheus
   - URL: http://prometheus:9090
3. Create dashboards for:
   - Application metrics (request rate, latency, errors)
   - Infrastructure (CPU, memory, network)
   - Chaos events timeline
   - RabbitMQ queue depth

### Key Metrics to Monitor

```
Traefik:
- traefik_http_requests_total
- traefik_http_request_duration_seconds

Application:
- Custom metrics from FastAPI (via prometheus middleware if added)

Infrastructure:
- node_cpu_seconds_total
- node_memory_MemAvailable_bytes
- container_memory_usage_bytes
- container_cpu_usage_seconds_total

RabbitMQ:
- rabbitmq_queue_messages_ready
- rabbitmq_queue_messages_unacked
```

## 🔄 Rolling Updates & Deployments

### Update microservice image

```bash
# Build new image
docker build -t localhost:5000/order-service:v2.0.0 ./FastAPI\ Application/services/order/
docker push localhost:5000/order-service:v2.0.0

# Update deployment
kubectl set image deployment/order-service order-service=localhost:5000/order-service:v2.0.0

# Monitor rollout
kubectl rollout status deployment/order-service

# Rollback if needed
kubectl rollout undo deployment/order-service
```

## 🛠️ Troubleshooting

### Pods not starting

```bash
# Check pod events
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # if crashed

# Check resource requests
kubectl describe nodes
```

### Database connection issues

```bash
# Test PostgreSQL connectivity
kubectl run -it --rm debug --image=postgres:14 --restart=Never -- \
  psql -h postgres-auth -U postgres -d auth_db

# Check RabbitMQ connectivity
kubectl run -it --rm debug --image=rabbitmq:3.11 --restart=Never -- \
  bash -c 'rabbitmqctl -n rabbit status'
```

### HTTPS certificate issues

```bash
# Check cert-manager logs
kubectl logs -n cert-manager deploy/cert-manager

# Check certificate status
kubectl get certificate
kubectl describe certificate <cert-name>

# Check ClusterIssuer
kubectl get clusterissuer
kubectl describe clusterissuer letsencrypt-prod
```

### Traefik not routing traffic

```bash
# Check Traefik logs
kubectl logs -n traefik deploy/traefik

# Check IngressRoutes
kubectl get ingressroute
kubectl describe ingressroute <route-name>

# Check Traefik dashboard: https://traefik.devopsgeek.dev
```

## 📝 Configuration Files Overview

### Image Registry Configuration

Edit image references in deployment YAML files:

**Development (local registry)**:
```yaml
image: localhost:5000/auth-service:latest
imagePullPolicy: Always
```

**Production (Docker Hub)**:
```yaml
image: myusername/auth-service:v1.0.0
imagePullPolicy: IfNotPresent
```

### Database Configuration

Passwords are hardcoded in manifests (dev only). For production:

```bash
# Create secret
kubectl create secret generic postgres-credentials \
  --from-literal=password=$(openssl rand -base64 32)

# Reference in deployment
valueFrom:
  secretKeyRef:
    name: postgres-credentials
    key: password
```

## 🔐 Security Notes (Development Only)

⚠️ These manifests are for **development/testing only**. For production:

1. **Secrets Management**: Use sealed-secrets, external-secrets, or vault
2. **RBAC**: Implement least-privilege ServiceAccounts and Roles
3. **Network Policies**: Restrict pod-to-pod communication
4. **Resource Quotas**: Limit namespace resource usage
5. **Pod Security Policies**: Enforce security standards
6. **Image Registry**: Use private registries with authentication
7. **TLS**: Rotate certificates regularly, use strong cipher suites

## 📚 Additional Resources

- [Traefik Kubernetes Documentation](https://doc.traefik.io/traefik/providers/kubernetes-crd/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Chaos Mesh Documentation](https://chaos-mesh.org/docs/)
- [Locust Documentation](https://docs.locust.io/)
- [Prometheus & Grafana Best Practices](https://prometheus.io/docs/)

## 🤝 Support

For issues:
1. Check application logs: `kubectl logs -f deploy/<service>`
2. Check infrastructure logs: `kubectl describe <resource>`
3. Review manifests for misconfigurations
4. Check DNS resolution: `nslookup devopsgeek.dev`

---

**Created for chaos engineering experiments. Use responsibly!** 🎯
