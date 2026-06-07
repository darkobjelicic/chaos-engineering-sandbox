[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# Load Test — Discovery of Blocked Event Loop (without async fix)

**Date:** 07.06.2026.  
**Type:** Incident — discovered during routine load test  
**Target:** api-gateway  
**Tool:** k6  

---

## Context

After the circuit breaker was successfully implemented and verified (see `API-GW-After-Circuit-Breaker`), a new load test was started in preparation for the "After" chaos experiments. During this test a new hidden weakness in the circuit breaker implementation was discovered.

---

## Hypothesis

The api-gateway with circuit breaker and 5s timeouts handles a load of 15 VUs stably over an extended period.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 15 VUs |
| Duration | 55 min (planned) |
| Circuit breaker | Yes (pybreaker, fail_max=5, reset_timeout=30s) |
| httpx timeout | 5s |
| httpx calls | Synchronous (`httpx.get()`) inside async functions ⚠️ |

---

## Screenshots

**k6 Load Test panel — oscillating request rate:**

![](<Screenshot from 2026-06-07 00-19-37.png>)

> 15 VUs. `::browse` request rate oscillates and drops at intervals — a direct consequence of gateway restart cycles. Failed requests **~10-15 req/s** continuously. k6 p99 latency relatively low (~1ms) because successful requests pass quickly, but many do not pass at all.

---

**CPU and memory per pod:**

![](<Screenshot from 2026-06-07 00-19-57.png>)

> api-gateway CPU **spikes to 0.2 cores (200m limit!)** as soon as it receives traffic. CPU throttling prevents the event loop from responding to the liveness probe in time. Visible CPU/memory drops to 0 at intervals — those are the moments of crash and restart.

---

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 00-20-20.png>)

> Overall system looks relatively healthy (13.8 req/s, p95 11.5ms, 0% error rate) because Bookstore Overview looks at all services together — api-gateway restarts are lost in the noise of other healthy services.

---

**api-gateway Service Detail — 9 restarts:**

![](<Screenshot from 2026-06-07 00-20-34.png>)

> api-gateway: **9 pod restarts** in ~30 minutes of load testing. p95 latency **159ms** — higher than expected. Exit code for all restarts: **0** (graceful shutdown), not a crash — Kubernetes sends SIGTERM because the liveness probe did not respond in time.

---

**Pod Count — multiple crashes:**

![](<Screenshot from 2026-06-07 00-20-54.png>)

> Pod Count drops to 0 **4-5 times**. CPU usage spikes to 0.2 cores as soon as the pod becomes active, then drops to 0 on restart. Memory stable (~48-64 MiB) — **not OOM**, but CPU throttling + event loop blocking.

---

## Root Cause Analysis

A combination of two problems:

### Problem 1 — Synchronous httpx blocks the event loop

```python
# ❌ Wrong — blocks the event loop
@app.get("/books")
async def proxy_list_books():
    @book_breaker
    def call():
        return httpx.get(f"{BOOK_SERVICE_URL}/books", timeout=TIMEOUT)
    r = call()  # synchronous call inside an async function!
```

FastAPI runs on an asyncio event loop. Synchronous `httpx.get()` blocks the entire event loop while waiting for a response. While the loop is blocked, no other request — including the `/health` liveness probe — can be served.

### Problem 2 — CPU limit and probe timeout are too short

- CPU limit: **200m** (0.2 cores) — too little for Python + FastAPI + pybreaker + OpenTelemetry under load
- Liveness probe timeout: **1s** — under CPU throttling, even an unblocked `/health` can take >1s
- 3 consecutive probe failures → Kubernetes sends SIGTERM → pod exits cleanly (Exit Code 0)

---

## Applied Fixes

### Fix 1 — asyncio.to_thread() for httpx calls

```python
# ✅ Correct — httpx runs in thread pool, event loop stays free
async def _call(breaker, fn):
    try:
        return await asyncio.to_thread(breaker(fn))
    except pybreaker.CircuitBreakerError:
        return None
```

`asyncio.to_thread()` executes the synchronous function in a ThreadPoolExecutor without blocking the event loop. The `/health` endpoint stays available even under full load.

### Fix 2 — Increased resources and probe timeout for api-gateway

```yaml
# deploy/overlays/kind/kustomization.yaml
resources:
  requests: { cpu: 100m, memory: 128Mi }
  limits:   { cpu: 500m, memory: 256Mi }   # 200m → 500m CPU
livenessProbe:
  timeoutSeconds: 5    # 1s → 5s
readinessProbe:
  timeoutSeconds: 5    # 1s → 5s
```

---

## Findings

- **Synchronous I/O in async code** is a hidden, hard-to-spot weakness — the system works under low load but crashes under real load
- Exit Code 0 and "Reason: Completed" in kubectl describe are key indicators: the pod did not crash, **Kubernetes killed it** due to probe timeouts
- CPU throttling at 200m was the trigger — without it the event loop might have been able to respond to the probe in time
- This is an example of a weakness that **would not have been discovered without a load test** — in a dev environment with 1-2 users everything works normally

## Conclusion

**Hypothesis rejected.** A new weakness discovered despite the previous "successful" circuit breaker test. Demonstrates a key principle of chaos engineering: **every round of testing can reveal a new layer of problems**. Fix: asyncio.to_thread + increased CPU limit + longer probe timeout. Verification in the next test _(see: Load-Test-With-Async)_.
