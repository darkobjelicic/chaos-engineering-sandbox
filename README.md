# chaos-engineering-sandbox

A microservices-based bookstore application built as a platform for chaos engineering experiments. Demonstrates a production-grade DevOps setup including GitOps, full-stack observability, load testing, and controlled failure injection via Chaos Mesh.

![CI](https://github.com/darkobjelicic/chaos-engineering-sandbox/actions/workflows/ci.yml/badge.svg)
![CD](https://github.com/darkobjelicic/chaos-engineering-sandbox/actions/workflows/cd.yml/badge.svg)

---

## Architecture

6 FastAPI microservices communicating via REST and RabbitMQ events, deployed on Kubernetes with a full observability and chaos engineering stack.

```
Frontend (React)
    └── API Gateway  ← circuit breaker per downstream service
         ├── Auth Service      → PostgreSQL
         ├── Book Service      → PostgreSQL
         ├── Order Service     → PostgreSQL → RabbitMQ
         └── Inventory Service → PostgreSQL ← RabbitMQ
                                               ↑
                                    Notification Service
```

---

## Stack

| Layer | Tools |
|-------|-------|
| Application | FastAPI, React |
| Containers | Docker, Docker Compose |
| Orchestration | Kubernetes (kind), Helm, Kustomize |
| GitOps | ArgoCD (automated sync + self-heal) |
| Observability | Prometheus, Grafana, Loki, Tempo, OpenTelemetry |
| Chaos Engineering | Chaos Mesh |
| Load Testing | k6 |
| CI/CD | GitHub Actions |
| Security | Sealed Secrets, Network Policies |

---

## Quick Start

### Prerequisites

- Docker 24+, kubectl, kind, Helm, k6
- See [docs/local-setup.md](docs/local-setup.md) for install instructions

### Linux — set inotify limits (required once, for Promtail)

```bash
sudo sysctl fs.inotify.max_user_instances=512
sudo sysctl fs.inotify.max_user_watches=524288
```

### Spin up the full stack

```bash
make cluster-up   # ~10-15 min — creates kind cluster, installs everything
```

Add to `/etc/hosts`:
```
127.0.0.1  bookstore.local api.bookstore.local grafana.monitoring.local
```

| Dashboard | URL | Credentials |
|-----------|-----|-------------|
| Grafana | http://grafana.monitoring.local | admin / admin |
| ArgoCD | `make argocd-ui` → localhost:8080 | admin / (see below) |

```bash
# ArgoCD password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
```

### Tear down

```bash
make cluster-down
```

---

## Running on Your Machine

**Clone and run** — just works, no configuration needed. All images are public on Docker Hub, ArgoCD syncs from this public repo.

**Fork and own the pipeline** — update `repoURL` in `deploy/argocd/bookstore-app.yaml`, image names in `cd.yml` and `kustomization.yaml`, and add `DOCKER_USERNAME` / `DOCKER_PASSWORD` as GitHub Actions secrets.

Full details in [docs/local-setup.md](docs/local-setup.md#running-on-your-machine-two-scenarios).

---

## Chaos Experiments

| Experiment | Target | Key Finding |
|---|---|---|
| Stress test (Before CB) | api-gateway | 6 pod restarts, p95 latency 4-5s @ 50 VUs |
| Stress test (After CB) | api-gateway | 0 restarts, 0 5xx errors — circuit breaker isolates failures |
| Network latency | book-service DB | DB connection pool hit 75%, latency propagated to clients |
| Pod failure | order-service | Kubernetes recovered; failure isolated, other services unaffected |
| HTTP 500 injection | order-service | 55% 4xx rate, api-gateway destabilized without circuit breaker |

Full experiment report with screenshots: [docs/chaos-experiments-report.md](docs/chaos-experiments-report.md)

---

## Makefile Reference

```bash
make cluster-up       # create kind cluster + full stack
make cluster-down     # delete cluster
make cluster-status   # show nodes and ArgoCD apps

make stress           # run stress test (50 VUs, finds breaking point)
make load             # run load test  (10 VUs, sustained)
make smoke            # run smoke test (quick sanity check)

make chaos-run EXPERIMENT=pod-failure-order   # run a chaos experiment

make grafana-ui       # port-forward Grafana to localhost:3001
make argocd-ui        # port-forward ArgoCD to localhost:8080
```

---

## Documentation

- [Local Setup & Onboarding](docs/local-setup.md)
- [Chaos Experiment Report](docs/chaos-experiments-report.md)
- [ADR — Architecture Decision Records](docs/adr/)
- [Runbooks](docs/runbooks/)
