[🇷🇸 Srpski](README.md) | 🇬🇧 English

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
- See [docs/local-setup.en.md](docs/local-setup.en.md) for install instructions

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

Full details in [docs/local-setup.en.md](docs/local-setup.en.md#running-on-your-machine-two-scenarios).

---

## Chaos Experiments

Each experiment follows the hypothesis-driven methodology: define steady state → hypothesize → inject failure → observe → conclude.

### API Gateway Fine Tuning (4 iterations)

| Iteration | Change | Result |
|---|---|---|
| Before Circuit Breaker | — | 6 restarts @ 50 VUs, cascading failure |
| After Circuit Breaker | pybreaker + 5s timeout | 0 restarts, but hidden bug in code |
| Discovered event loop blocking | sync httpx in async functions | 9 restarts @ 15 VUs (SIGTERM) |
| asyncio.to_thread + resource fix | thread pool + CPU 500m + probe 5s | 0 restarts, 0 failed req/s |

### Chaos Experiments

| Experiment | Target | Before | After (CB + async) |
|---|---|---|---|
| Network latency (300ms DB) | book-service | Pool 75%, degraded | Stable, 0 errors, latency propagates |
| Pod failure | order-service | 3 restarts, ~14 failed req/s | 3 restarts, **~2 failed req/s**, CB absorbs |
| HTTP 500 (path: *) | order-service | 6 GW restarts, 8 OS restarts | 0 GW restarts, 9 OS restarts* |
| HTTP 500 (path: /orders*) | order-service | — | **0 restarts**, system stable |
| CPU stress 80% | inventory-service | — | Latency propagates, 0 errors, CB does not trip |

*path: `*` hit the `/health` endpoint — fixed in the third iteration

Full experiment details with screenshots: [docs/experiments/](docs/experiments/)  
Architecture decisions: [docs/adr/](docs/adr/)  
Operational runbooks: [docs/runbooks/](docs/runbooks/)

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

- [Local Setup & Onboarding](docs/local-setup.en.md)
- [ADR — Architecture Decision Records](docs/adr/)
- [Runbooks](docs/runbooks/)
- [Chaos Experiments](docs/experiments/)
