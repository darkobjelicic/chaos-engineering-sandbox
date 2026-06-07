[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# HTTP 500 Injection — order-service (after circuit breaker + async fix)

**Date:** 07.06.2026.  
**Type:** Chaos experiment — HTTPChaos  
**Target:** order-service  
**Tool:** Chaos Mesh + k6  

---

## Context

Same experiment as `http-500-order-Before-Circuit-Breaker`, run after implementing the circuit breaker and asyncio.to_thread fix. The goal is to verify that the api-gateway no longer crashes when a downstream service returns errors.

**Note:** During this experiment an additional problem was discovered — the Chaos Mesh configuration uses `path: "*"` which includes the `/health` endpoint. The liveness probe on order-service receives a 500 response and Kubernetes restarts the pod. The 1s liveness probe timeout further worsens the situation under load. Fix (timeout 1s → 5s for all services) applied after this test.

---

## Hypothesis

The circuit breaker on the api-gateway will prevent cascading failure — the api-gateway will not crash when order-service returns HTTP 500 errors.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 15 VUs |
| Chaos type | HTTPChaos — replace response code |
| Injected error | HTTP 500 on all responses (path: "*") |
| Duration | 2 minutes |
| Circuit breaker | Yes (fail_max=5, reset_timeout=30s) |
| Liveness probe timeout | 1s (not yet fixed) |

---

## Screenshots

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 14-39-19.png>)

> Overall system: 46.6 req/s, p95 **79.6ms**, error rate **5.14%**, active pods **11** (order-service restarting). Chaos experiment visible at ~14:30. api-gateway latency briefly spikes but the system does not crash.

---

**Errors & Health:**

![](<Screenshot from 2026-06-07 14-39-33.png>)

> api-gateway 5xx error rate grows to **~12.5%** — these are 503 responses returned by the circuit breaker while the circuit is open. order-service 4xx rate reaches **~80%** (Chaos Mesh injects 500 on all paths). Active HTTP requests stay at max **3** — no connection accumulation.

---

**CPU and memory:**

![](<Screenshot from 2026-06-07 14-39-42.png>)

> api-gateway CPU stable at ~40% throughout the test. order-service CPU drops during restart. Other services completely unaffected.

---

**k6 Load Test:**

![](<Screenshot from 2026-06-07 14-39-51.png>)

> 15 VUs. Failed requests reach **~2 req/s** at the moment of the chaos experiment — same as in the pod-failure experiment. Browse operations remain stable (~25-30 req/s). p99 latency stays below **1.5ms**.

---

**order-service dashboard:**

![](<Screenshot from 2026-06-07 14-40-05.png>)

> order-service: request rate drops to **0 req/s** during the chaos experiment, **9 pod restarts** — Chaos Mesh injects 500 on the `/health` endpoint too so liveness probe fails. This is the direct motivation for fixing the probe timeout on all services.

---

**api-gateway dashboard — key screenshot:**

![](<Screenshot from 2026-06-07 14-40-14.png>)

> api-gateway: 24.9 req/s, p95 **201ms**, 5xx error rate **13.2%**, restarts **= 0**. api-gateway DOES NOT CRASH. 5xx errors are 503 responses from the circuit breaker — visible and controlled, not hidden behind pod crashes as in the previous scenario.

---

**notification-service (isolation check):**

![](<Screenshot from 2026-06-07 14-40-22.png>)

> notification-service: **0 restarts**, p95 **4.75ms** — completely stable.

---

## Before and after comparison

| Metric | Before (no CB) | After (CB + async) |
|---|---|---|
| api-gateway restarts | **6** | **0** |
| order-service restarts | 8 | 9* |
| api-gateway 5xx | Hidden (pod crash) | **13.2% (503 from CB)** |
| order-service 4xx | ~55% | **~80%** |
| k6 Failed requests (peak) | High, continuous | **~2 req/s, brief** |
| Active HTTP requests | Accumulate | **Max 3** |
| api-gateway stable | No | **Yes** |
| Errors visible in metrics | No | **Yes** |

*order-service has more restarts because Chaos Mesh hits `/health` too — root cause resolved by increasing probe timeout to 5s for all services.

---

## Findings

- **api-gateway does not crash** (0 restarts) — circuit breaker successfully isolates errors
- 5xx errors (13.2%) are now **visible and expected** — circuit breaker returns 503 instead of the gateway crashing. This is an observability improvement: in the previous scenario errors were hidden behind pod crashes
- order-service restarts because of the Chaos Mesh configuration (`path: "*"`) which hits the liveness probe — note for future experiments: use a more specific path (e.g. `/orders*`)
- Active HTTP requests stay minimal — no thundering herd effect

## Conclusion

**Hypothesis confirmed.** Circuit breaker eliminates cascading failure. api-gateway remains stable regardless of downstream service errors. Two side problems discovered:
1. `path: "*"` in the HTTPChaos configuration hits health endpoints — use a more specific path in future experiments
2. Liveness probe timeout of 1s is too short for all Python services — **fixed** by increasing to 5s in the kustomization overlay
