[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# Pod Failure — order-service (after circuit breaker + async fix)

**Date:** 07.06.2026.  
**Type:** Chaos experiment — PodChaos  
**Target:** order-service  
**Tool:** Chaos Mesh + k6  

---

## Context

Same experiment as `pod-failure-order-Before-Circuit-Breaker`, run after implementing the circuit breaker and asyncio.to_thread fix. The goal is to verify that the protection mechanisms improve system behavior during a pod failure.

---

## Hypothesis

The circuit breaker on the api-gateway will prevent cascading failure during an order-service pod failure. The api-gateway will not crash, and failed requests will be minimal and short-lived.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 15 VUs |
| Chaos type | PodChaos — pod-failure |
| Mode | one (kills one pod) |
| Duration | 2 minutes |
| Circuit breaker | Yes (fail_max=5, reset_timeout=30s) |
| httpx | asyncio.to_thread |

---

## Screenshots

**Bookstore Overview — system-wide view:**

![](<Screenshot from 2026-06-07 14-20-09.png>)

> Overall system: **80.1 req/s**, p95 latency **82.7ms**, error rate **0%**, active pods **12**. Chaos experiment clearly visible (~13:55, red dashed lines) as a brief latency spike on the api-gateway, but the system remains functional.

---

**Errors & Health:**

![](<Screenshot from 2026-06-07 14-20-24.png>)

> api-gateway 5xx error rate reaches **~12.5%** in a brief window during the chaos experiment while the circuit breaker activates, then immediately drops to **0%**. No 4xx errors. Active HTTP requests stay at minimum (1-3) — no accumulation of blocked connections.

---

**CPU and memory per pod:**

![](<Screenshot from 2026-06-07 14-20-34.png>)

> api-gateway CPU stable at ~40% throughout the test. order-service CPU drops to 0 at the moment of the chaos experiment and returns on restart. Other services completely unaffected.

---

**k6 Load Test panel:**

![](<Screenshot from 2026-06-07 14-20-44.png>)

> 15 VUs. Failed requests reach only **~2 req/s** at the brief moment of the chaos experiment — then immediately drop back to 0. p99 latency stays below **0.7ms** for browse and **0.5ms** for order. System recovers in seconds.

---

**order-service dashboard:**

![](<Screenshot from 2026-06-07 14-21-01.png>)

> order-service: **3 pod restarts**, p95 latency **93.3ms**, error rate **0%**. Pod Count drops and returns, but the system continues serving requests as soon as the pod becomes available.

---

**api-gateway dashboard:**

![](<Screenshot from 2026-06-07 14-21-09.png>)

> api-gateway: 19.3 req/s, p95 **98.8ms**, 5xx error rate **0%**, restarts **= 0**. Key difference from the previous experiment where api-gateway had 5 restarts — here it has none.

---

**notification-service (isolation check):**

![](<Screenshot from 2026-06-07 14-21-19.png>)

> notification-service: **0 restarts**, p95 **4.75ms** — completely stable, failure did not spread.

---

## Before and after comparison

| Metric | Before (no CB) | After (CB + async) |
|---|---|---|
| api-gateway restarts | 5 | **0** |
| k6 Failed requests (peak) | ~14 req/s | **~2 req/s** |
| Duration of failed requests | Continuous | **Brief spike** |
| 5xx error rate (peak) | Hidden (pod crash) | **~12.5% → quickly 0%** |
| System recovery | Slow, unstable | **Fast, automatic** |
| api-gateway stable | No | **Yes** |

---

## Findings

- Circuit breaker absorbs the order-service pod failure — api-gateway no longer crashes
- Failed requests are **7x lower** and short-lived (~2 req/s for seconds vs ~14 req/s continuously)
- 5xx errors are now visible in metrics (brief spike to ~12.5%) because the gateway returns 503 instead of crashing — this is an **observability improvement**
- Kubernetes self-healing still works — order-service recovers without intervention
- Failure isolation confirmed — notification-service, book-service and others completely unaffected

## Conclusion

**Hypothesis confirmed.** The circuit breaker prevents cascading failure during a pod failure. The api-gateway remains stable (0 restarts), failed requests are minimal and short-lived, and the system recovers automatically and quickly.
