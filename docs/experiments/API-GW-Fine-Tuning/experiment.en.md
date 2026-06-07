[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# API Gateway Fine Tuning — Iterative Discovery and Elimination of Weaknesses

**Period:** 25.05.2026. – 07.06.2026.  
**Target:** api-gateway  
**Type:** Iterative load test + hardening  

---

## Overview

This is not one experiment but **four iterations** of the same stress test, each revealing a new layer of weakness. It demonstrates how chaos engineering works in practice — not as a one-time check, but as a continuous improvement cycle.

```
Iteration 1  →  Iteration 2  →  Iteration 3  →  Iteration 4
Before CB        After CB         Event loop       After asyncio
                                  blocking          + resource fix
                                  discovered
```

---

## Iteration 1 — Baseline: gateway crashes under load

**Date:** 25.05.2026. | **Folder:** `API-GW-Before-Circuit-Breaker/`

**Configuration:** 50 VUs, httpx with no timeouts, no circuit breaker.

![](<../API-GW-Before-Circuit-Breaker/Screenshot from 2026-05-25 22-58-33.png>)

> **6 pod restarts**, p95 latency 4-5s. httpx calls with no timeouts accumulate connections until resources are exhausted. Classic cascading failure.

**Hypothesis rejected.** Identified need for circuit breaker and HTTP timeouts.

**Change applied:**
- Added `pybreaker==1.0.2`
- Circuit breaker per service: `fail_max=5, reset_timeout=30s`
- httpx timeout: `5s` on all calls

---

## Iteration 2 — After circuit breaker: more stable, but...

**Date:** 26.05.2026. | **Folder:** `API-GW-After-Circuit-Breaker/`

**Configuration:** 50 VUs, circuit breaker active.

![](<../API-GW-After-Circuit-Breaker/Screenshot from 2026-05-26 19-47-59.png>)

> **0 new restarts**, 0 5xx errors, p95 1.46s. Circuit breaker eliminates cascading failure. System passes stress test.

**Hypothesis confirmed.** But the implementation has a hidden bug that only manifests under prolonged operation.

---

## Iteration 3 — Discovery: synchronous httpx blocks the event loop

**Date:** 07.06.2026. | **Folder:** `Load-Test-Without-Async/`

**Configuration:** 15 VUs, longer load test, circuit breaker active.

![](<../Load-Test-Without-Async/Screenshot from 2026-06-07 00-20-34.png>)

> **9 pod restarts** in 30 minutes. Exit Code 0 — Kubernetes sends SIGTERM because the liveness probe does not respond in time. Root cause: synchronous `httpx.get()` inside `async` functions blocks the event loop so `/health` cannot respond within the timeout.

```python
# Wrong — blocks event loop
async def proxy_list_books():
    @book_breaker
    def call():
        return httpx.get(f"{BOOK_SERVICE_URL}/books", timeout=TIMEOUT)
    r = call()  # synchronous call blocks the entire event loop!
```

**Combination of problems:**
1. Synchronous httpx in async functions → event loop blocked
2. CPU limit 200m → Python under load cannot respond to probe in time
3. Liveness probe timeout 1s → too short for Python under pressure

**Change applied:**
```python
# Correct — thread pool, event loop stays free
async def _call(breaker, fn):
    try:
        return await asyncio.to_thread(breaker(fn))
    except pybreaker.CircuitBreakerError:
        return None
```
- `asyncio.to_thread()` for all httpx calls
- CPU limit: `200m → 500m`
- Probe timeout: `1s → 5s`

---

## Iteration 4 — Verification: stable system

**Date:** 07.06.2026. | **Folder:** `Load-Test-With-Async/`

**Configuration:** 15 VUs, 55 min sustained load.

![](<../Load-Test-With-Async/Screenshot from 2026-06-07 13-34-38.png>)

> **Restarts = 0**, **Failed requests = 0**, CPU stable at ~40%, Pod Count = 1 throughout the entire test.

![](<../Load-Test-With-Async/Screenshot from 2026-06-07 13-33-20.png>)

> k6: 0 failed requests during 55 minutes. Browse ~25-30 req/s, order ~2-3 req/s. p99 ~1.5ms.

**Hypothesis confirmed.** System stable under sustained load.

---

## Evolution across iterations

| Metric | Iter. 1 | Iter. 2 | Iter. 3 | Iter. 4 |
|---|---|---|---|---|
| VUs | 50 | 50 | 15 | 15 |
| Pod restarts | **6** | 0 | **9** | **0** |
| k6 Failed req/s | ~14 | ~14-20 | ~10-15 | **0** |
| 5xx errors | Hidden | 0 | 0 | **0** |
| System stable | No | Yes* | No | **Yes** |
| Exit code of crash | — | — | 0 (SIGTERM) | — |

*Stable but with a hidden bug in the code

---

## Lessons Learned

1. **Circuit breaker is not enough** — the implementation must be async-correct. Adding a synchronous library to async code introduces subtle bugs that are not visible under low load.

2. **Probe timeout must match the application's characteristics** — 1s is too little for a Python application under CPU load. The timeout should be less than `httpx_timeout` but large enough for normal latency.

3. **CPU limit is part of the SLA** — too little CPU = throttling = health check timeouts = unnecessary restarts. Resource limits must be calibrated to actual load.

4. **Chaos engineering is iterative** — every round of testing can reveal a new layer of problems that the previous one did not show.
