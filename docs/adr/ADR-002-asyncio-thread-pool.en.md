[🇷🇸 Srpski](ADR-002-asyncio-thread-pool.md) | 🇬🇧 English

# ADR-002: asyncio.to_thread for httpx calls in api-gateway

**Status:** Accepted  
**Date:** 07.06.2026.  

---

## Context

After implementing the circuit breaker (ADR-001), a load test with 15 VUs showed that api-gateway continued to crash — but in a different way. The Exit Code was 0 (graceful shutdown), not a crash, indicating that Kubernetes was sending SIGTERM due to liveness probe timeouts.

Root cause analysis:

```python
# Problematic code — synchronous httpx inside async function
async def proxy_list_books():
    @book_breaker
    def call():
        return httpx.get(f"{BOOK_SERVICE_URL}/books", timeout=TIMEOUT)
    r = call()  # blocks the asyncio event loop!
```

FastAPI uses the asyncio event loop. A synchronous `httpx.get()` call blocks the entire event loop while waiting for the HTTP response. During that time, no other coroutine can execute — including the liveness probe endpoint `/health`. Kubernetes fails the probe 3 times (3 × 1s timeout = 3s) and sends SIGTERM, the pod shuts down cleanly (Exit Code 0).

This did not appear in earlier tests because 50 VUs is a short burst session. With 15 VUs and a long sustained test, throttling at 200m CPU + blocked event loop = reliable failure.

---

## Decision

Execute all synchronous httpx calls in a **ThreadPoolExecutor** using `asyncio.to_thread()`, freeing the event loop for other tasks.

```python
async def _call(breaker, fn):
    try:
        return await asyncio.to_thread(breaker(fn))
    except pybreaker.CircuitBreakerError:
        return None
```

Additionally:
- CPU limit increased: `200m → 500m`
- Liveness/readiness probe timeout: `1s → 5s` (for api-gateway and all other Python services)

---

## Alternatives Considered

**A) Native async httpx (`httpx.AsyncClient`)**  
Cleaner solution — `httpx.AsyncClient` natively supports `await`. Problem: `pybreaker` is a synchronous library and does not support async calls. Requires replacing `pybreaker` with an async-compatible circuit breaker (e.g., `aiobreaker`) or writing a custom implementation.

**B) asyncio.to_thread (chosen)**  
Keeps `pybreaker` and the existing logic, only moves synchronous calls to a thread pool. Smaller scope of change, easier to review. Threading overhead is negligible for I/O-bound work.

**C) Increasing CPU limit without code fix**  
Could reduce the frequency of the problem but does not fix the root cause — the event loop would still be blocked, just less often.

---

## Consequences

- api-gateway stable under sustained load — 0 restarts during 55-minute test with 15 VUs
- k6 failed requests: 0 (vs ~10-15/s before the fix)
- Threading overhead: negligible for I/O-bound operations (HTTP calls)
- CPU usage ~40% of 500m limit under load — room for growth
- Probe timeout of 5s introduced for all Python services as the same issue can affect any service under CPU pressure
