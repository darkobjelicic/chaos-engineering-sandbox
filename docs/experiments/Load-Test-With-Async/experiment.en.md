[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# Load Test — Verification of asyncio.to_thread + resource fix (with async fix)

**Date:** 07.06.2026.  
**Type:** Verification load test — confirming the fix  
**Target:** api-gateway  
**Tool:** k6  

---

## Context

After the blocked event loop and CPU throttling issue was discovered (see `Load-Test-Without-Async`), three fixes were applied:

| Fix | Change |
|---|---|
| asyncio.to_thread | httpx calls execute in a thread pool — event loop stays free |
| CPU limit | 200m → 500m (0.2 → 0.5 cores) |
| Probe timeout | 1s → 5s (liveness + readiness) |

This load test serves as verification that all three fixes together solve the problem.

---

## Hypothesis

The api-gateway with asyncio.to_thread fix and increased resources handles a load of 15 VUs without a single pod restart and without failed requests.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 15 VUs |
| Duration | 55 min sustained |
| httpx calls | `asyncio.to_thread()` — async ✅ |
| CPU limit | 500m |
| Memory limit | 256Mi |
| Probe timeout | 5s |

---

## Screenshots

**k6 Load Test panel:**

![](<Screenshot from 2026-06-07 13-33-20.png>)

> 15 stable VUs. `::browse` request rate **~25-30 req/s**, `::order` **~2-3 req/s**. k6 p99 latency ~1.5ms. **Failed requests = 0** — a dramatic difference from the previous test where failed was ~10-15 req/s continuously.

---

**CPU and memory per pod:**

![](<Screenshot from 2026-06-07 13-33-42.png>)

> api-gateway CPU grows to ~40% and **stabilizes** — no drops to 0 that marked restart cycles. Memory stable at ~48-64 MiB. Pod no longer restarts.

---

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 13-34-01.png>)

> Overall system: **76.9 req/s**, p95 latency **107ms**, error rate **0%**, active pods **12** — all green.

---

**api-gateway Service Detail — key screenshot:**

![](<Screenshot from 2026-06-07 13-34-38.png>)

> api-gateway: 34.8 req/s, p95 latency **245ms**, 5xx error rate **0%**, restarts **= 0**. Pod Count stays stable at 1 throughout the entire test. CPU grows to ~0.4 cores but does not cause a restart — the event loop is free thanks to asyncio.to_thread.

---

**order-service (control):**

![](<Screenshot from 2026-06-07 13-35-06.png>)

> order-service: 4.55 req/s, p95 **206ms**, 0 restarts, CPU ~0.08 cores — stable.

---

**book-service (control):**

![](<Screenshot from 2026-06-07 13-35-15.png>)

> book-service: 21.9 req/s, p95 **4.99ms**, 0 restarts, CPU ~0.06 cores — stable and fast.

---

## Comparison with previous test

| Metric | Without async fix | With async fix |
|---|---|---|
| Pod restarts | 9 in ~30 min | **0** |
| k6 Failed requests | ~10-15 req/s | **0 req/s** |
| Pod Count stability | Drops to 0 multiple times | **Stable at 1** |
| Error rate (5xx) | 0% (pod crashes before responding) | **0%** |
| CPU pattern | Spike → drop → spike → drop | **Grows and stabilizes** |
| System usable | No | **Yes** |

---

## Findings

- **asyncio.to_thread eliminates event loop blocking** — the health endpoint responds even under full CPU load
- CPU grows to ~40% and stabilizes — threading overhead is real but acceptable
- 0 failed requests throughout the entire test — the system is **fully available** under 15 VUs
- Latency on api-gateway (~245ms p95) is higher than on direct services because the gateway is an extra hop + thread pool overhead
- Memory stays stable at ~48-64 MiB — well below the 256Mi limit

## Conclusion

**Hypothesis confirmed.** All three fixes together solve the problem. The api-gateway is ready for chaos experiments. This closes the iterative cycle: problem discovered under load → root cause analyzed → fix applied → verified.
