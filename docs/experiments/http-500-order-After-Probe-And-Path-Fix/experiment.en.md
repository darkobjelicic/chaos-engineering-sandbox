[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# HTTP 500 Injection — order-service (after probe + path configuration fix)

**Date:** 07.06.2026.  
**Type:** Chaos experiment — HTTPChaos (Iteration 3)  
**Target:** order-service  
**Tool:** Chaos Mesh + k6  

---

## Context

Third iteration of the HTTP 500 experiment. In addition to the circuit breaker and asyncio fix, two more improvements discovered in the previous iteration were applied:

1. **Chaos path narrowed** — `path: "*"` → `path: "/orders*"` so the `/health` endpoint is not affected
2. **Probe timeout increased** — 1s → 5s for all Python services

This is the final verification that the system correctly handles HTTP 500 errors without side effects.

---

## Hypothesis

With all fixes applied, the system will handle HTTP 500 errors on order-service without a single pod restart (neither api-gateway nor order-service) and with minimal failed requests.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 15 VUs |
| Chaos type | HTTPChaos — replace response code |
| Injected error | HTTP 500 only on `/orders*` |
| Duration | 2 minutes |
| Circuit breaker | Yes (fail_max=5, reset_timeout=30s) |
| Probe timeout | 5s (all services) |

---

## Screenshots

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 15-10-23.png>)

> Overall system: **56.5 req/s**, p95 **149ms**, error rate **0%**, active pods **12**. Brief latency spike on api-gateway during chaos experiment (~15:03), but the system never loses stability.

---

**Errors & Health:**

![](<Screenshot from 2026-06-07 15-10-36.png>)

> api-gateway 5xx error rate reaches **~14%** briefly while the circuit breaker opens, then immediately drops to **0%**. No 4xx errors. Active HTTP requests stay normal — no connection accumulation.

---

**CPU and memory:**

![](<Screenshot from 2026-06-07 15-10-45.png>)

> All services stable. No dramatic CPU/memory drops that would indicate restart cycles.

---

**k6 Load Test:**

![](<Screenshot from 2026-06-07 15-10-57.png>)

> 15 VUs. Failed requests reach **~6 req/s** briefly during the chaos experiment then immediately drop to 0. Browse operations (~20-25 req/s) minimally affected. p99 latency stays below **2ms**.

---

**order-service — key screenshot:**

![](<Screenshot from 2026-06-07 15-11-09.png>)

> order-service: 2.46 req/s, p95 **159ms**, error rate **0%**, restarts **= 0**. Pod Count stable at 1 throughout the entire test. Direct confirmation that the path fix (`/orders*`) protects the `/health` endpoint from chaos injection.

---

**api-gateway:**

![](<Screenshot from 2026-06-07 15-11-16.png>)

> api-gateway: 17.8 req/s, p95 **231ms**, 5xx error rate **0%** (after chaos experiment), restarts **= 0**. Circuit breaker does its job and returns to normal state.

---

**notification-service (isolation check):**

![](<Screenshot from 2026-06-07 15-11-24.png>)

> notification-service: **0 restarts**, p95 **4.75ms** — completely stable.

---

## Evolution across three iterations

| Metric | Iteration 1 (before CB) | Iteration 2 (CB + async) | Iteration 3 (+ probe + path) |
|---|---|---|---|
| api-gateway restarts | **6** | 0 | **0** |
| order-service restarts | 8 | **9** | **0** |
| k6 Failed req (peak) | High, continuous | ~2 req/s | **~6 req/s briefly** |
| Active pods | 10-11 | 11 | **12** |
| Total error rate | Hidden | 5.14% | **0%** |
| System stable | No | Partially | **Yes** |
| Chaos hits /health | — | Yes | **No** |

*Note: Failed requests in Iteration 3 (~6/s) are higher than Iteration 2 (~2/s) because the circuit breaker can now normally reject and return 503 without a pod crash — errors are controlled and visible, not hidden behind restarts.

---

## Findings

- **0 restarts** on all services — the system behaves exactly as designed
- "Not much happened" is **proof of success** — the goal of chaos engineering is not for the system to feel no failure, but to withstand it without collapse
- Circuit breaker opens the circuit, returns 503 to clients, waits for reset_timeout (30s), probes again — all per specification
- Specificity of the path in chaos experiments is critical — `path: "*"` is too aggressive for Python services with short probe timeouts

## Conclusion

**Hypothesis confirmed.** The final iteration demonstrates a system that correctly and predictably handles downstream service errors. Each of the three iterations revealed a new layer of improvements — the essence of chaos engineering methodology.
