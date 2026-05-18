# chaos-engineering-sandbox

A microservices-based bookstore application built as a platform for chaos engineering experiments. Demonstrates a production-grade DevOps setup including GitOps, observability, load testing, and controlled failure injection.

## Architecture

6 FastAPI microservices communicating via REST and RabbitMQ events, deployed on Kubernetes with a full observability and chaos engineering stack.

```
Frontend (React)
    └── API Gateway
         ├── Auth Service     → PostgreSQL
         ├── Book Service     → PostgreSQL
         ├── Order Service    → PostgreSQL → RabbitMQ
         └── Inventory Service → PostgreSQL ← RabbitMQ
                                               ↑
                                    Notification Service
```

## Stack

| Layer | Tools |
|-------|-------|
| Application | FastAPI, React |
| Containers | Docker, Docker Compose |
| Orchestration | Kubernetes (kind), Helm, Kustomize |
| GitOps | ArgoCD |
| Observability | Prometheus, Grafana, Loki, Tempo |
| Chaos Engineering | Chaos Mesh |
| Load Testing | k6 |
| CI/CD | GitHub Actions |
| Security | Sealed Secrets, Network Policies |

## Quick Start

### Local development
```bash
cp .env.example .env
make dev-up
```

### Full Kubernetes stack
```bash
make cluster-up
```

See [docs/local-setup.md](docs/local-setup.md) for prerequisites and detailed setup instructions.

## Documentation

- [Local Setup](docs/local-setup.md)
- [Architecture](docs/architecture.md)
- [Observability](docs/observability.md)
- [Chaos Runbook](docs/runbooks/chaos-experiment.md)
