[🇷🇸 Srpski](ADR-003-probe-timeout.md) | 🇬🇧 English

# ADR-003: Liveness/Readiness Probe Timeout — 5s for all Python services

**Status:** Accepted  
**Date:** 07.06.2026.

---

## Context

During the load test following the circuit breaker implementation (ADR-001), api-gateway continued to restart even after the event loop blocking issue was resolved (ADR-002). Analysis showed that the `/health` endpoint sometimes failed to respond within 1 second when the pod was under CPU pressure.

Kubernetes was configured with `timeoutSeconds: 1` for liveness and readiness probes on all services. Under load, a Python/FastAPI service running at 200m CPU can delay its response to HTTP requests — including health checks. Three consecutive timeouts (3 × 1s = 3s) trigger a SIGTERM and a graceful shutdown with Exit Code 0, which looks like an intentional restart rather than a crash.

The same scenario can affect any Python service in the cluster under sufficient CPU pressure, not just api-gateway.

---

## Decision

Increase `timeoutSeconds` for liveness and readiness probes from `1s` to `5s` on all Python services:

- `api-gateway`
- `book-service`
- `order-service`
- `auth-service`
- `inventory-service`
- `notification-service`

The change was applied to the corresponding Kubernetes Deployment manifests.

---

## Alternatives Considered

**A) Per-service tuning (considered as a starting point, then expanded)**  
Initially, tuning only api-gateway was considered since that was where the issue was observed. However, since all services share the same runtime (Python/FastAPI) and the same CPU limits, the decision was made to apply the change uniformly — before the same problem could trigger an incident on another service.

**B) Increasing CPU limits instead of timeout**  
Higher CPU limits reduce the probability of the service being slow, but do not eliminate it. Under sufficient load, even a 500m CPU service can delay a health check response. A 5s timeout is a safety layer independent of CPU configuration.

**C) Keeping 1s timeout**  
Too aggressive for Python services under real load. Kubernetes does not distinguish between "service is slow" and "service has crashed" — both scenarios lead to a restart, masking the actual root cause.

---

## Consequences

- All Python services tolerate brief health check response delays without unnecessary restarts
- Kubernetes remains effective at detecting genuinely broken pods — 5s timeout × 3 failures = 15s to SIGTERM, which is acceptable
- Uniform application of the change eliminates the risk of the same issue going undetected on other services
- The 5s probe timeout is a conservative value; it can be reduced if CPU limits are increased in the future
