[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# HTTP 500 Injection — order-service (before circuit breaker)

**Date:** 26.05.2026.  
**Type:** Chaos experiment — HTTPChaos  
**Target:** order-service  
**Tool:** Chaos Mesh + k6  

---

## Hypothesis

Injecting HTTP 500 errors on order-service responses will not cause the api-gateway to crash — the gateway will forward the errors to clients without crashing itself.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 15 VUs |
| Chaos type | HTTPChaos — replace response code |
| Injected error | HTTP 500 on all responses |
| Target port | 8000 |
| Duration | 2 minutes |
| Circuit breaker | No |

**Chaos Mesh configuration:**
```yaml
action: replace
target: Response
port: 8000
path: "*"
replace:
  code: 500
duration: 2m
```

---

## Screenshots

**api-gateway dashboard:**

![](<Screenshot from 2026-05-26 21-03-49.png>)

> api-gateway: **6 pod restarts**, p95 latency **3.90s**. Gateway receives continuous errors from order-service and cannot isolate them — it accumulates blocked connections until it crashes.

---

**order-service dashboard:**

![](<Screenshot from 2026-05-26 21-04-02.png>)

> order-service: **8 pod restarts**, p95 latency **982ms** then drops to **0 req/s** — service stopped receiving traffic because Kubernetes keeps restarting it due to liveness probe errors.

---

**DB connections — order-service:**

![](<Screenshot from 2026-05-26 21-04-16.png>)

> DB connections on order-service drop from 5 to 1 during the chaos experiment — service loses the ability to operate normally with the database.

---

**Bookstore Overview:**

![](<Screenshot from 2026-05-26 21-04-37.png>)

> Overall system: p95 latency **2.54s**, active pods dropped to **11** (order-service is down). api-gateway latency dominates the graph.

---

**Errors & Health — Bookstore Overview:**

![](<Screenshot from 2026-05-26 21-04-51.png>)

> **4xx error rate on order-service reaches ~55%** during the chaos experiment. 5xx visible on api-gateway. Chaos events marked with red dashed lines.

---

**CPU and memory:**

![](<Screenshot from 2026-05-26 21-05-02.png>)

> api-gateway CPU and memory oscillate in sync with restart cycles. Other services stable.

---

**k6 Load Test:**

![](<Screenshot from 2026-05-26 21-05-13.png>)

> 15 VUs. `::order` requests drop to **0** during the chaos experiment — clients cannot reach order-service. `::browse` operations still work — partial system availability.

---

**notification-service (isolation check):**

![](<Screenshot from 2026-05-26 21-07-26.png>)

> notification-service: **0 restarts**, p95 latency **~9ms** — stable. Errors did not spread further in the system.

---

## Findings

- HTTP 500 errors from order-service **propagated upward** and caused api-gateway instability (6 restarts)
- Critical difference from the pod-failure experiment: the service is physically available but returning errors — an api-gateway without a circuit breaker cannot distinguish a temporary error from a permanent failure
- Gateway holds connections open, accumulates errors, crashes — classic **thundering herd** problem
- 4xx error rate on order-service ~55% — Chaos Mesh successfully injected errors on more than half of responses
- `::browse` operations survived — the system was **partially available**

## Conclusion

**Hypothesis rejected.** An api-gateway without a circuit breaker cannot isolate downstream service errors. Instead of quickly returning an error to the client, the gateway holds connections open until it crashes. This is the direct motivation for introducing a circuit breaker — demonstrated in the `API-GW-After-Circuit-Breaker` experiment.
