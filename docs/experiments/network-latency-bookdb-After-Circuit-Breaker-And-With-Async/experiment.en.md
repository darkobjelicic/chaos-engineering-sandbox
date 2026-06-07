[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# Network Latency — book-service database (after circuit breaker + async fix)

**Date:** 07.06.2026.  
**Type:** Chaos experiment — NetworkChaos  
**Target:** book-service → PostgreSQL (postgres-book)  
**Tool:** Chaos Mesh + k6  

---

## Context

Same experiment as `network-latency-bookdb-Before-Circuit-Breaker`, run after the circuit breaker and asyncio.to_thread fix. The goal is to see whether system behavior has changed.

---

## Hypothesis

The system will handle 300ms network latency toward the book-service database. The api-gateway will not crash. The DB connection pool will not be exhausted.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 15 VUs |
| Chaos type | NetworkChaos — delay |
| Injected latency | 300ms ± 50ms, 50% correlation |
| Duration | 2 minutes |
| Circuit breaker | Yes |
| httpx timeout | 5s |

---

## Screenshots

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 13-52-30.png>)

> Overall system: **54.4 req/s**, p95 **85.4ms**, error rate **0%**, active pods **12**. Two chaos events visible (~13:40). p95 latency per service shows a large spike on api-gateway (~10s) and book-service during the chaos window — 300ms DB latency multiplies through the request chain.

---

**CPU and memory:**

![](<Screenshot from 2026-06-07 13-52-43.png>)

> api-gateway CPU **drops** during the chaos experiment (less work since fewer requests pass through) then recovers. All other services stable. No restart cycles.

---

**k6 Load Test:**

![](<Screenshot from 2026-06-07 13-52-54.png>)

> 15 VUs. `::browse` request rate **drops sharply** during the chaos experiment (~13:40-13:42) because book-service responds slowly. After the chaos experiment ends, browse recovers. Failed requests stay practically at **0** — system degraded but without errors.

---

**book-service dashboard:**

![](<Screenshot from 2026-06-07 13-53-15.png>)

> book-service: 22.2 req/s, p95 **4.84ms** (measured after chaos period), error rate **0%**, restarts **0**. Latency spikes sharply during the chaos experiment.

---

**api-gateway dashboard:**

![](<Screenshot from 2026-06-07 13-53-23.png>)

> api-gateway: 19.2 req/s, p95 **96.4ms**, error rate **0%**, restarts **0**. Latency spikes sharply during the chaos experiment (p99 → ~8-9s) because the gateway waits for a response from the slow book-service — close to the 5s httpx timeout boundary.

---

**inventory-service (control):**

![](<Screenshot from 2026-06-07 13-53-45.png>)

> inventory-service: 11.1 req/s, p95 **4.82ms**, 0 restarts — completely unaffected.

---

## Before and after comparison

| Metric | Before (no CB/async) | After (CB + async) |
|---|---|---|
| api-gateway restarts | 0 | **0** |
| DB connection pool peak | **~75%** | Not available (Grafana) |
| k6 Failed requests | ~8-14 req/s | **~0 req/s** |
| api-gateway latency (p99) | ~4-5s | **~8-9s** (higher!) |
| System stable | Yes (degraded) | **Yes (degraded)** |
| Browse available | Yes (degraded) | **Yes (degraded)** |

*Note: api-gateway p99 latency is higher in the After scenario because asyncio.to_thread holds the connection open until the httpx timeout (5s) instead of blocking the event loop and crashing. This is correct behavior.

---

## Findings

- Network latency toward the database **still propagates** to clients — the circuit breaker does not protect against a slow service that does not return errors
- api-gateway **does not crash** (0 restarts) — the asyncio.to_thread fix keeps the event loop free
- Browse request rate drops because the gateway waits for a response that is delayed ~300ms+
- httpx **5s timeout** is the protection that would, if latency exceeded that threshold, convert slowness into an error and trigger the circuit breaker
- Unlike the previous scenario, there is no accumulation of blocked connections

## Conclusion

**Hypothesis confirmed.** The system handles network latency without crashes or errors. Key finding: the circuit breaker and timeout together make the system predictable — either responses arrive within the timeout (5s), or the circuit breaker trips. Clean degradation instead of chaotic crash.
