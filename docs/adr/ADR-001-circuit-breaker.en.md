[🇷🇸 Srpski](ADR-001-circuit-breaker.md) | 🇬🇧 English

# ADR-001: Circuit Breaker in api-gateway

**Status:** Accepted  
**Date:** 26.05.2026.  

---

## Context

A stress test with 50 virtual users showed that the api-gateway crashed **6 times** during the test. The httpx HTTP client had no timeout configured for calls to downstream services (book-service, order-service, auth-service, inventory-service). Under load, connections to slow or unavailable services would accumulate, exhaust resources and cause an OOM/crash cycle that repeated as long as load was active.

Grafana metrics showed the gateway crashing (Exit Code != 0, pod restarts) but with no visible 5xx errors in HTTP metrics — the error was lost at the connection level, not the HTTP layer.

---

## Decision

Implement the **circuit breaker pattern** in api-gateway using the `pybreaker` library, with a separate circuit breaker per downstream service.

Configuration:
- `fail_max = 5` — open circuit after 5 consecutive failures
- `reset_timeout = 30s` — half-open state after 30 seconds
- `httpx timeout = 5s` — every HTTP call is cut off after 5 seconds

When the circuit is open, the gateway immediately returns `503 Service Unavailable` instead of waiting and accumulating connections.

---

## Alternatives Considered

**A) HTTP timeouts only (no circuit breaker)**  
Timeout prevents infinite waiting, but without a circuit breaker every request still attempts to contact the broken service. Under high load, 5s timeout × N VUs = resources can still be exhausted.

**B) Retry with exponential backoff**  
Useful for short transient errors, but without a circuit breaker creates a "thundering herd" — all clients retry simultaneously and further overload an already broken service.

**C) pybreaker (chosen)**  
Combination of timeouts and circuit breaker: timeout limits the duration of a single call, circuit breaker limits the number of attempts toward a broken service. Circuit opens, gateway returns fast 503s, downstream service gets room to recover.

**D) Hystrix / Resilience4j**  
JVM ecosystem, not applicable for Python.

---

## Consequences

- api-gateway no longer crashes under load — 0 new restarts in verification test
- 5xx errors now **visible** in metrics (503 from CB) instead of hidden behind pod crashes — improved observability
- Added dependency: `pybreaker==1.0.2`
- Note: circuit breaker protects against errors, not against slow downstream services. The 5s timeout is the protection against slowness.
