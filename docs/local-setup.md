# Local Setup

## System Requirements

| Resource | Minimum |
|----------|---------|
| CPU | 4 cores |
| RAM | 8 GB (16 GB recommended for full stack) |
| Disk | 20 GB free |
| OS | Linux / macOS |

---

## Required Tools

### Container & Orchestration

| Tool | Version | Install |
|------|---------|---------|
| [Docker](https://docs.docker.com/engine/install/) | 24+ | `apt-get install docker-ce` |
| [Docker Compose](https://docs.docker.com/compose/install/) | v2.20+ | Included with Docker Desktop |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | v1.28+ | `apt-get install kubectl` |
| [kind](https://kind.sigs.k8s.io/docs/user/quick-start/) | v0.20+ | Binary from GitHub releases |
| [Helm](https://helm.sh/docs/intro/install/) | v3.12+ | `apt-get install helm` |

### GitOps & Secrets

| Tool | Version | Install |
|------|---------|---------|
| [argocd CLI](https://argo-cd.readthedocs.io/en/stable/cli_installation/) | v2.10+ | Binary from GitHub releases |
| [kubeseal](https://github.com/bitnami-labs/sealed-secrets#installation) | v0.26+ | Binary from GitHub releases |

### Testing

| Tool | Version | Install |
|------|---------|---------|
| [k6](https://k6.io/docs/get-started/installation/) | v0.50+ | Binary from GitHub releases |

### Code Quality

| Tool | Version | Install |
|------|---------|---------|
| [pre-commit](https://pre-commit.com/#installation) | v3.0+ | `pipx install pre-commit` |

---

## Quick Install (Ubuntu 24.04)

### argocd CLI
```bash
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd && sudo mv argocd /usr/local/bin/
```

### kubeseal
```bash
curl -sSL -o kubeseal.tar.gz "https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.36.6/kubeseal-0.36.6-linux-amd64.tar.gz"
tar -xzf kubeseal.tar.gz kubeseal
chmod +x kubeseal && sudo mv kubeseal /usr/local/bin/
rm kubeseal.tar.gz
```

### k6
```bash
curl -fsSL https://github.com/grafana/k6/releases/download/v0.57.0/k6-v0.57.0-linux-amd64.tar.gz -o k6.tar.gz
tar -xzf k6.tar.gz
sudo mv k6-v0.57.0-linux-amd64/k6 /usr/local/bin/
rm -rf k6.tar.gz k6-v0.57.0-linux-amd64
```

### pre-commit
```bash
sudo apt-get install -y pipx
pipx install pre-commit
pipx ensurepath
```

---

## Verify Installation

```bash
docker --version
docker compose version
kubectl version --client
kind --version
helm version
argocd version --client
kubeseal --version
k6 version
pre-commit --version
```

---

## Local Development (Docker Compose)

Start all services locally without Kubernetes:

```bash
cp .env.example .env   # edit values if needed
make dev-up
```

Services available at:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Gateway | http://localhost:8000 |
| RabbitMQ UI | http://localhost:15672 (guest/guest) |
| Adminer (DB) | http://localhost:8081 |

Stop:
```bash
make dev-down
```

---

## Full Local Stack (Kubernetes + GitOps)

Spin up the complete stack with a single command:

```bash
make cluster-up
```

This script will:
1. Create a kind cluster
2. Install NGINX Ingress Controller
3. Install cert-manager
4. Install ArgoCD
5. ArgoCD pulls everything else from this repo automatically

Access points after bootstrap:

```bash
make argocd-ui    # ArgoCD dashboard
make grafana-ui   # Grafana (metrics, logs, traces)
```

Tear down:
```bash
make cluster-down
```
