[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# Stress Test — api-gateway (before circuit breaker)

**Date:** 25.05.2026.  
**Type:** Load / Stress test  
**Target:** api-gateway  
**Tool:** k6  

---

## Hypothesis

The system will handle a load of 50 virtual users without service crashes. The api-gateway will forward requests to downstream services and return responses with reasonable latency.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 50 VUs |
| Ramp-up | 2 min → 50% → 3 min → 100% |
| Duration | ~10 min sustained |
| Endpoint | `http://api.bookstore.local` |
| httpx timeout | ∞ (not configured) |
| Circuit breaker | No |

---

## Screenshots

**api-gateway dashboard — start of test:**

![](<Screenshot from 2026-05-25 22-58-33.png>)

> p95 latency jumped to **939ms**, **6 pod restarts** visible immediately. Pod count oscillates between 0 and 1 as Kubernetes continuously recreates the pod.

---

![](<Screenshot from 2026-05-25 22-59-24.png>)

> Request rate drops to nearly 0 during pod restarts. Latency spikes sharply (p99 > 4s).

---

**Bookstore Overview — system-wide view:**

![](<Screenshot from 2026-05-25 23-03-06.png>)

> Overall system p95 latency **2.01s**. api-gateway dominates latency compared to all other services.

---

**CPU and memory per pod:**

![](<Screenshot from 2026-05-25 23-03-33.png>)

> api-gateway CPU usage spikes and drops in sync with restarts. Other services stable and unaffected.

---

**k6 Load Test panel:**

![](<Screenshot from 2026-05-25 23-04-47.png>)

> 50 active VUs. k6 records **~14 failed req/s** continuously. `::browse` request rate spikes and drops in sync with restart cycles. `::order` is practically unavailable.

---

**Errors & Health:**

![](<Screenshot from 2026-05-25 23-22-40.png>)

> The 5xx errors panel shows "No data" — the gateway crashes (SIGTERM) before it can return an HTTP error response. The error is lost at the connection level, not the HTTP layer.

---

## Findings

- api-gateway crashed **6 times** during the test
- Root cause: `httpx` with no timeouts — connections to downstream services accumulate until resources are exhausted, causing an OOM/crash cycle that repeats as long as load is active
- Kubernetes restarts the pod, but the situation repeats as soon as the new pod receives traffic
- Classic **cascading failure** — one slow upstream is enough to bring down the gateway
- 5xx errors are not visible in metrics because the pod crashes before it can respond

## Conclusion

**Hypothesis rejected.** The system cannot sustain 50 VUs without protection mechanisms. Identified need for a circuit breaker and HTTP timeouts on all downstream calls.
