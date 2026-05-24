.DEFAULT_GOAL := help

# ─── Variables ────────────────────────────────────────────────────────────────
CLUSTER_NAME  := chaos-sandbox
KIND_CONFIG   := scripts/kind-config.yaml
OVERLAY       ?= kind
ENV           ?= kind

BASE_URL_kind := http://api.bookstore.local
BASE_URL_prod := https://api.devopsgeek.dev
BASE_URL      ?= $(BASE_URL_$(ENV))
VUS           ?= 10
DURATION      ?= 25m

# ─── Help ─────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  chaos-engineering-sandbox"
	@echo ""
	@echo "  Local development"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  make dev-up          Start all services (docker compose)"
	@echo "  make dev-down        Stop all services"
	@echo "  make dev-logs        Tail all service logs"
	@echo ""
	@echo "  Kubernetes cluster"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  make cluster-up      Create kind cluster + bootstrap full stack"
	@echo "  make cluster-down    Delete kind cluster"
	@echo "  make cluster-status  Show cluster and ArgoCD status"
	@echo ""
	@echo "  Deploy"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  make deploy          Apply kustomize overlay (OVERLAY=dev|prod)"
	@echo "  make argocd-ui       Open ArgoCD UI in browser"
	@echo "  make grafana-ui      Open Grafana UI in browser"
	@echo ""
	@echo "  Testing"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  make smoke           Run smoke test  (ENV=kind|prod)"
	@echo "  make load            Run load test   (ENV=kind|prod)"
	@echo "  make stress          Run stress test (ENV=kind|prod)"
	@echo "  make chaos-run       Run chaos experiment (EXPERIMENT=<name>)"
	@echo ""
	@echo "  Code quality"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  make lint            Run pre-commit hooks on all files"
	@echo "  make lint-install    Install pre-commit hooks"
	@echo ""

# ─── Local development ────────────────────────────────────────────────────────
.PHONY: dev-up
dev-up:
	docker compose up --build -d

.PHONY: dev-down
dev-down:
	docker compose down -v

.PHONY: dev-logs
dev-logs:
	docker compose logs -f

# ─── Cluster ──────────────────────────────────────────────────────────────────
.PHONY: cluster-up
cluster-up:
	@bash scripts/cluster-up.sh

.PHONY: cluster-down
cluster-down:
	kind delete cluster --name $(CLUSTER_NAME)

.PHONY: cluster-status
cluster-status:
	@kubectl get nodes
	@echo ""
	@kubectl get applications -n argocd 2>/dev/null || echo "ArgoCD not installed yet"

# ─── Deploy ───────────────────────────────────────────────────────────────────
.PHONY: deploy
deploy:
	kubectl apply -k deploy/overlays/$(OVERLAY)

.PHONY: argocd-ui
argocd-ui:
	@echo "ArgoCD: http://localhost:8080"
	@echo "User: admin"
	@echo "Pass: $$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"
	kubectl port-forward svc/argocd-server -n argocd 8080:443

.PHONY: grafana-ui
grafana-ui:
	@echo "Grafana: http://localhost:3001"
	@echo "User: admin / Pass: admin"
	kubectl port-forward svc/grafana -n monitoring 3001:80

# ─── Testing ──────────────────────────────────────────────────────────────────
.PHONY: smoke
smoke:
	BASE_URL=$(BASE_URL) VUS=$(VUS) bash scripts/run-load-test.sh load-testing/k6/scripts/smoke.js

.PHONY: load
load:
	BASE_URL=$(BASE_URL) VUS=$(VUS) DURATION=$(DURATION) bash scripts/run-load-test.sh load-testing/k6/scripts/load.js

.PHONY: stress
stress:
	BASE_URL=$(BASE_URL) VUS=$(VUS) DURATION=$(DURATION) bash scripts/run-load-test.sh load-testing/k6/scripts/stress.js

.PHONY: chaos-run
chaos-run:
	@bash scripts/run-chaos.sh $(EXPERIMENT)

# ─── Code quality ─────────────────────────────────────────────────────────────
.PHONY: lint
lint:
	pre-commit run --all-files

.PHONY: lint-install
lint-install:
	pre-commit install
