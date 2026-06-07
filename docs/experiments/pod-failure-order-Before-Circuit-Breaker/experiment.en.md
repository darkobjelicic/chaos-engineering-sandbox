[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# Pod Failure — order-service (before circuit breaker)

**Date:** 26.05.2026.  
**Type:** Chaos experiment — PodChaos  
**Target:** order-service  
**Tool:** Chaos Mesh + k6  

---

## Hypothesis

Kubernetes will detect the order-service pod failure and restart it within a reasonable time. The system will be temporarily degraded during the restart cycle but will recover. Other services will not be affected.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 15 VUs |
| Chaos type | PodChaos — pod-failure |
| Mode | one (kills one pod) |
| Duration | 2 minutes (repeated) |
| Circuit breaker | No |

**Chaos Mesh configuration:**
```yaml
action: pod-failure
mode: one
selector:
  labelSelectors:
    app: order-service
duration: 2m
```

---

## Screenshots

**order-service dashboard:**

![](<Screenshot from 2026-05-26 20-51-49.png>)

> **3 pod restarts** visible. p95 latency on order-service reaches **~1.67s**. Red dashed lines mark the moments of the chaos experiment.

---

**Bookstore Overview:**

![](<Screenshot from 2026-05-26 20-52-06.png>)

> Overall system: p95 latency **2.15s**, request rate ~15 req/s. Latency rises on all services that depend on order-service at the moment of failure.

---

**CPU and memory per pod:**

![](<Screenshot from 2026-05-26 20-52-23.png>)

> Two red dashed lines (two chaos events) clearly visible. order-service CPU and memory drop to 0 during the failure, spike back on restart.

---

**DB and Disk:**

![](<Screenshot from 2026-05-26 20-52-32.png>)

> DB connections for order-service drop to 0 during the chaos experiment and recover after restart. Disk I/O spikes on restart (connection initialization).

---

**k6 Load Test panel:**

![](<Screenshot from 2026-05-26 20-52-42.png>)

> 15 VUs. At the moment of the chaos experiment (~20:43 and ~20:45), `::order` latency spikes to **~7ms p99**, failed requests peak at **~14 req/s**. System recovered between the two events.

---

**api-gateway dashboard (control):**

![](<Screenshot from 2026-05-26 20-53-19.png>)

> api-gateway: **5 restarts** (from earlier test), but no new crashes during this experiment. p95 ~2.39s — sensing the slow connection toward the failed order-service.

---

**notification-service (isolation check):**

![](<Screenshot from 2026-05-26 20-53-52.png>)

> notification-service: **0 restarts**, p95 latency **7.33ms** — completely stable. Confirms the failure was isolated to order-service.

---

## Findings

- Pod failure caused **short periods of unavailability** (duration of restart cycle ~30-60s)
- Kubernetes successfully restarted the pod within a reasonable time
- **Failure isolation worked** — notification-service, book-service, auth-service were not affected
- During restart, requests to order-service fail immediately without a retry mechanism
- api-gateway feels the failure (increased latency) but does not crash itself

## Conclusion

**Hypothesis confirmed.** Kubernetes self-healing works. The failure was isolated without propagating to other services. Weakness: no retry logic on the api-gateway side — requests arriving during the restart fail immediately instead of waiting or retrying.
