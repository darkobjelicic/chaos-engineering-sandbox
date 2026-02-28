# 🚀 Chaos Engineering Sandbox - Complete K8s Deployment

## ⚡ Quick Start

```bash
# 1. Build and push Docker images
./build-and-push.sh localhost:5000 latest

# 2. Deploy to Kubernetes
./deploy.sh localhost:5000 dev

# 3. Wait for services to be ready
kubectl get pods -w

# 4. Add DNS records (or use port-forwarding for testing)

# 5. Access services:
#    - App: https://devopsgeek.dev
#    - Grafana: https://grafana.devopsgeek.dev
#    - Load test: kubectl port-forward svc/locust-master 8089:8089
```

## 📁 Project Structure

```
chaos-engineering-sandbox/
├── FastAPI Application/          # Python microservices (existing)
│   ├── services/
│   │   ├── auth/
│   │   ├── book/
│   │   ├── order/
│   │   ├── inventory/
│   │   ├── notification/
│   │   └── gateway/
│   └── frontend/                 # React app
│
├── k8s/                          # Kubernetes manifests (NEW!)
│   ├── base/                     # Core components
│   ├── traefik/                  # Ingress controller
│   ├── cert-manager/             # HTTPS certificates
│   ├── monitoring/               # Prometheus + Grafana
│   ├── chaos-mesh/               # Chaos experiments
│   ├── locust/                   # Load testing
│   ├── overlays/                 # Dev/Prod configurations
│   ├── kustomization.yaml        # Root kustomize config
│   └── README.md                 # Detailed K8s docs
│
├── deploy.sh                     # One-command deployment script
├── build-and-push.sh            # Build & push Docker images
├── docker-compose.yml            # Local dev (existing)
└── README.md                     # This file
```

## 🎯 What's Included

### ✅ Microservices (K8s Deployed)
- **Auth Service** - JWT authentication
- **Book Service** - Catalog management
- **Order Service** - Order processing
- **Inventory Service** - Stock management (consumes RabbitMQ events)
- **Notification Service** - Event notifications (RabbitMQ consumer)
- **API Gateway** - Routes requests to services
- **React Frontend** - Web UI

### ✅ Infrastructure
- **PostgreSQL** - 4 separate databases (auth, book, inventory, order)
- **RabbitMQ** - Message broker with management UI
- **Traefik** - Ingress controller with automatic routing
- **cert-manager** - Automatic HTTPS with Let's Encrypt

### ✅ Monitoring
- **Prometheus** - Metrics collection
- **Grafana** - Dashboards & visualization

### ✅ Chaos Engineering
- **Chaos Mesh** - Automated chaos experiments:
  - Pod kills (random pod termination)
  - Network delays (latency injection)
  - Packet loss (network unreliability)
  - CPU stress (resource exhaustion)
  - Pod failures (graceful shutdown)

### ✅ Load Testing
- **Locust** - Distributed load testing:
  - Master-worker architecture
  - Simulates concurrent users
  - Web UI for real-time monitoring
  - Custom test scenarios (register, login, order, etc.)

## 🚀 Deployment Steps

### 1. Prerequisites

```bash
# Install kubectl (if not already installed)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# Install kustomize
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
sudo mv kustomize /usr/local/bin/

# Configure kubectl
scp user@cluster:/path/to/kubeconfig ~/.kube/config
# OR
export KUBECONFIG=/path/to/kubeconfig

# Verify cluster connection
kubectl cluster-info
kubectl get nodes
```

### 2. Build Docker Images

```bash
# Make scripts executable
chmod +x build-and-push.sh deploy.sh

# Build and push to local registry in cluster
./build-and-push.sh localhost:5000 latest

# OR push to Docker Hub
./build-and-push.sh myusername latest
```

### 3. Deploy to Kubernetes

```bash
# Deploy everything in one command
./deploy.sh localhost:5000 dev

# OR manually with kustomize
cd k8s/
kustomize build . | kubectl apply -f -

# Verify deployment
kubectl get pods
kubectl get svc
```

### 4. Configure DNS

Get the LoadBalancer IP:
```bash
kubectl get svc -n traefik traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

Add DNS A records pointing to this IP:
- `devopsgeek.dev`
- `www.devopsgeek.dev`
- `app.devopsgeek.dev`
- `grafana.devopsgeek.dev`
- `prometheus.devopsgeek.dev`
- `traefik.devopsgeek.dev`
- `rabbitmq.devopsgeek.dev`

Or for testing without DNS:
```bash
# Port-forward services
kubectl port-forward -n traefik svc/traefik 80:80 443:443 &
kubectl port-forward svc/grafana 3000:3000 &
```

## 🌐 Access Services

Once DNS is configured:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | https://devopsgeek.dev | - |
| **API Gateway** | https://app.devopsgeek.dev | - |
| **Grafana** | https://grafana.devopsgeek.dev | admin/admin |
| **Prometheus** | https://prometheus.devopsgeek.dev | - |
| **RabbitMQ** | https://rabbitmq.devopsgeek.dev | guest/guest |
| **Traefik** | https://traefik.devopsgeek.dev | - |

## 🧪 Run Chaos Engineering Tests

### 1. Start Load Test

```bash
# Port-forward to Locust web UI
kubectl port-forward svc/locust-master 8089:8089

# Open browser: http://localhost:8089
# - Number of users: 100
# - Spawn rate: 10
# - Click "Start swarming"
```

### 2. Monitor in Grafana

```bash
# Open Grafana dashboard
# https://grafana.devopsgeek.dev

# Create panels to monitor:
# - Request latency (traefik_http_request_duration_seconds)
# - Error rate (traefik_http_requests_total with status=5xx)
# - Pod restarts
# - RabbitMQ queue depth
```

### 3. Trigger Chaos Experiments

The chaos experiments run automatically based on cron schedule:
- Pod kills every 2 minutes
- Network delays every 3 minutes
- Packet loss every 5 minutes
- CPU stress every 4 minutes
- Pod failures every 6 minutes

Or manually trigger:
```bash
# Kill a pod immediately
kubectl delete pod -l app=order-service

# View chaos experiments
kubectl get podchaos
kubectl get networkchaos
kubectl describe podchaos kill-order-service-pod

# Disable a chaos experiment
kubectl delete podchaos kill-order-service-pod
```

### 4. Observe System Behavior

While Locust is running and chaos experiments are active:

**In Grafana:**
- ⏱️ Watch request latency spike during network delays
- 📊 See error rate increase during pod kills
- 🔄 Monitor pod restarts and recovery time
- 📈 Check resource usage during CPU stress

**In Traefik Dashboard:**
- View real-time requests
- Check endpoint health
- Monitor traffic distribution

**In RabbitMQ:**
- Watch queue depth changes
- Monitor message throughput
- Check consumer acknowledgments

## 📊 Example Chaos Test Scenario

```bash
# Scenario: Test order service resilience under load + chaos

# Terminal 1: Start Locust load test
kubectl port-forward svc/locust-master 8089:8089
# Open http://localhost:8089, start 500 users

# Terminal 2: Monitor Grafana
kubectl port-forward svc/grafana 3000:3000
# Open http://localhost:3000, create dashboard

# Terminal 3: Watch Chaos Mesh experiments
watch -n 2 'kubectl get podchaos,networkchaos,stresschaos'

# Terminal 4: Check application logs
kubectl logs -f deploy/order-service

# Observations to track:
# 1. Baseline metrics (before chaos)
# 2. Metrics during pod kill (should see spike in errors)
# 3. Recovery time (how long until requests succeed again)
# 4. RabbitMQ queue behavior (messages pile up? get processed?)
# 5. Overall system stability
```

## 🔍 Monitoring & Debugging

### Check Deployment Status

```bash
# All pods
kubectl get pods -A

# Specific namespace
kubectl get pods -n default

# Pod details
kubectl describe pod <pod-name>

# Pod logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # if crashed
kubectl logs -f <pod-name>          # follow logs

# Recent events
kubectl get events --sort-by='.lastTimestamp'
```

### Check Services

```bash
# All services
kubectl get svc -A

# Service details
kubectl describe svc <service-name>

# Service endpoints
kubectl get endpoints <service-name>
```

### Check Ingress Routes

```bash
# Traefik ingress routes
kubectl get ingressroute

# Route details
kubectl describe ingressroute <route-name>

# Traefik dashboard
https://traefik.devopsgeek.dev
```

### Database Connectivity

```bash
# Test PostgreSQL
kubectl run -it --rm debug --image=postgres:14 --restart=Never -- \
  psql -h postgres-auth -U postgres -d auth_db

# Test RabbitMQ
kubectl run -it --rm debug --image=rabbitmq:3.11 --restart=Never -- \
  rabbitmq-diagnostics -q ping
```

## 🛠️ Troubleshooting

### Issue: Pods not starting
```bash
# Check pod events
kubectl describe pod <pod-name>

# Check node resources
kubectl top nodes
kubectl top pods
```

### Issue: Services not accessible
```bash
# Check ingress routes
kubectl get ingressroute
kubectl describe ingressroute <route-name>

# Check Traefik logs
kubectl logs -n traefik deploy/traefik

# Check certificate status
kubectl get certificate
kubectl describe certificate <cert-name>
```

### Issue: Database connection errors
```bash
# Check database pod status
kubectl logs deploy/postgres-auth

# Verify database exists
kubectl run -it --rm debug --image=postgres:14 --restart=Never -- \
  psql -h postgres-auth -U postgres -c "\l"
```

### Issue: RabbitMQ not processing messages
```bash
# Check RabbitMQ status
kubectl logs deploy/rabbitmq

# Check queue status
kubectl port-forward svc/rabbitmq 15672:15672
# Open http://localhost:15672 (guest/guest)

# Check consumer logs
kubectl logs -f deploy/inventory-service
kubectl logs -f deploy/notification-service
```

## 📚 Additional Resources

- **K8s Docs**: See `k8s/README.md` for detailed documentation
- **Traefik**: https://doc.traefik.io/traefik/
- **cert-manager**: https://cert-manager.io/
- **Chaos Mesh**: https://chaos-mesh.org/
- **Locust**: https://docs.locust.io/
- **Prometheus**: https://prometheus.io/docs/
- **Grafana**: https://grafana.com/docs/

## 📝 Notes

- **Development only**: These manifests are for testing/learning. For production, implement proper secrets management, RBAC, network policies, etc.
- **Resource requirements**: Minimum 8GB RAM on cluster for all components
- **Persistent storage**: Uses local storage classes - for production use proper storage provisioners
- **Security**: Default passwords and open endpoints - not suitable for production

## 🎯 Next Steps

1. ✅ Deploy to K8s
2. ✅ Run load tests with Locust
3. ✅ Trigger chaos experiments
4. ✅ Monitor in Grafana
5. 📊 Analyze resilience
6. 🔧 Improve application based on findings
7. 🚀 Deploy to production with proper configurations

---

Made for chaos engineering experimentation 🎯
