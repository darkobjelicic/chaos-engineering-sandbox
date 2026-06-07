[🇷🇸 Srpski](local-setup.md) | 🇬🇧 English

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

## Linux: inotify Limits (required for Promtail)

Promtail watches container log files using inotify. The Linux default limits are too low for a kind cluster. Run once before `cluster-up.sh`:

```bash
sudo sysctl fs.inotify.max_user_instances=512
sudo sysctl fs.inotify.max_user_watches=524288
```

To make it permanent across reboots:
```bash
echo "fs.inotify.max_user_instances=512" | sudo tee -a /etc/sysctl.conf
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf
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

---

## Running on Your Machine (Two Scenarios)

### Scenario A — Just run it (clone & go)

The repo is fully self-contained and publicly accessible. No extra configuration needed.

```bash
git clone https://github.com/darkobjelicic/chaos-engineering-sandbox.git
cd chaos-engineering-sandbox

# Linux only — required for Promtail (see inotify section above)
sudo sysctl fs.inotify.max_user_instances=512
sudo sysctl fs.inotify.max_user_watches=524288

make cluster-up
```

Add to `/etc/hosts`:
```
127.0.0.1  bookstore.local api.bookstore.local grafana.monitoring.local
```

**Why this just works:**
- All application secrets are plain literals in `kustomization.yaml` (dev credentials — safe for a local sandbox)
- All Docker images are public on Docker Hub (`darko999/*`)
- ArgoCD syncs from the public GitHub repo — no auth required
- Everything else is pulled from public Helm/kubectl registries during `cluster-up`

**Limitation:** You won't be able to push your own code changes and have CI/CD build new images — that requires Docker Hub credentials configured in GitHub Actions.

---

### Scenario B — Fork and own the full pipeline

If you want your own CI/CD pipeline that builds and deploys your changes:

**1. Fork the repo on GitHub**

**2. Update the ArgoCD application to point to your fork:**
```yaml
# deploy/argocd/bookstore-app.yaml
spec:
  source:
    repoURL: https://github.com/YOUR-USERNAME/chaos-engineering-sandbox.git
```

**3. Update image names in the CD workflow:**
```yaml
# .github/workflows/cd.yml — replace all occurrences of darko999 with your Docker Hub username
image: YOUR-DOCKERHUB-USERNAME/api-gateway
# ... repeat for each service
```

**4. Update image names in the kustomization overlay:**
```yaml
# deploy/overlays/kind/kustomization.yaml — replace darko999 with your Docker Hub username
images:
- name: YOUR-DOCKERHUB-USERNAME/api-gateway
  newName: YOUR-DOCKERHUB-USERNAME/api-gateway
```

**5. Add GitHub Actions secrets** in your fork's Settings → Secrets → Actions:
```
DOCKER_USERNAME   your Docker Hub username
DOCKER_PASSWORD   your Docker Hub access token
```

**6. Run the stack:**
```bash
make cluster-up
```

From this point, every push to `main` will automatically build new images, update image tags, and ArgoCD will deploy to your local cluster.
