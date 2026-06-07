[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# Network Latency — book-service database (before circuit breaker)

**Date:** 26.05.2026.  
**Type:** Chaos experiment — NetworkChaos  
**Target:** book-service → PostgreSQL (postgres-book)  
**Tool:** Chaos Mesh + k6  

---

## Hypothesis

Introducing 300ms (±50ms) network latency between book-service and its database will propagate to clients as increased latency, but the system will remain functional without service crashes.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 15 VUs |
| Chaos type | NetworkChaos — delay |
| Injected latency | 300ms ± 50ms (jitter), 50% correlation |
| Duration | 2 minutes |
| Circuit breaker | No |

**Chaos Mesh configuration:**
```yaml
action: delay
delay:
  latency: 300ms
  jitter: 50ms
  correlation: "50"
direction: to
selector:
  labelSelectors:
    app: book-service
```

---

## Screenshots

**Bookstore Overview — Errors & Health:**

![](<Screenshot from 2026-05-26 20-38-12.png>)

> No 5xx or 4xx errors. Active HTTP requests on api-gateway oscillate normally. The service is **available but degraded**.

---

**CPU and memory per pod:**

![](<Screenshot from 2026-05-26 20-38-26.png>)

> api-gateway CPU usage visibly higher (~15-20%) during the chaos period — holding connections open longer while waiting for the slow book-service.

---

**DB and Disk — Bookstore Overview:**

![](<Screenshot from 2026-05-26 20-38-37.png>)

> Spike in DB connections for book-service around 20:30 — connections stay open longer because each query waits for a response. Disk I/O Read spikes to ~80 MB/s as a result of retry logic and longer transaction hold time.

---

**book-service dashboard:**

![](<Screenshot from 2026-05-26 20-39-49.png>)

> p95 latency on book-service jumped to **436ms**. Request rate **5.24 req/s**, error rate **0%**.

---

**DB Connection Pool Utilization:**

![](<Screenshot from 2026-05-26 20-40-03.png>)

> DB Connection Pool Utilization reaches **~75%** at the moment of the chaos experiment. Critical level — at 100% new requests start waiting in queue or fail immediately.

---

**k6 Load Test:**

![](<Screenshot from 2026-05-26 20-38-48.png>)

> 15 VUs. `::browse` latency grows during the test (from ~3ms to ~5ms p99). Failed requests oscillate between **~8 and ~14 req/s**.

---

## Findings

- Network latency toward the database propagates directly to end users (increased latency on browse operations)
- The service **does not crash** — it remains functional but degraded
- DB connection pool reached **75% utilization** — in production with more VUs the pool would be exhausted
- Disk I/O spikes due to longer transaction duration
- No mechanism to quickly "cut off" the slow database and protect the rest of the system

## Conclusion

**Hypothesis partially confirmed.** The system remains functional but latency propagates to clients. Critical finding: 75% DB connection pool utilization at only 15 VUs is a warning signal. In a production scenario with more users the pool would be exhausted and cause a failure. Recommendation: add timeout on DB connections and alerting when connection pool exceeds 60%.
