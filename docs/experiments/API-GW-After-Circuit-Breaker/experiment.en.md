[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# Stress Test — api-gateway (after circuit breaker)

**Date:** 26.05.2026.  
**Type:** Load / Stress test  
**Target:** api-gateway  
**Tool:** k6  

---

## Hypothesis

Introducing a circuit breaker (pybreaker, fail_max=5, reset_timeout=30s) and 5s timeouts on httpx calls will prevent cascading failure. The api-gateway will not crash under a load of 50 VUs.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 50 VUs |
| Ramp-up | 2 min → 50% → 3 min → 100% |
| Duration | ~10 min sustained |
| httpx timeout | 5s |
| Circuit breaker | pybreaker (fail_max=5, reset_timeout=30s) |
| Code change | `pybreaker==1.0.2` added to requirements |

---

## Screenshots

**api-gateway dashboard:**

![](<Screenshot from 2026-05-26 19-47-36.png>)

> **5 pod restarts** visible at the beginning (old pods from previous state). No new crashes during the test itself. p95 latency more stable.

---

**Bookstore Overview:**

![](<Screenshot from 2026-05-26 19-47-59.png>)

> Overall system p95 latency **1.46s** — lower than the previous scenario. All **12 pods remain Running** throughout the entire test.

---

**Errors & Health:**

![](<Screenshot from 2026-05-26 19-48-15.png>)

> **No data for 5xx and 4xx errors** — the circuit breaker takes over traffic and returns fast 503 responses instead of waiting and crashing. Active HTTP requests shows a normal pattern with no connection accumulation.

---

**DB and Disk panel:**

![](<Screenshot from 2026-05-26 19-49-03.png>)

> DB connections stable, Disk I/O Read spikes to ~35 MB/s during intense load period — normal behavior under load.

---

**k6 Load Test panel:**

![](<Screenshot from 2026-05-26 19-49-16.png>)

> 50 VUs. p99 latency for `::browse` **~15ms**, for `::order` **~15ms** — a dramatic improvement over the previous test. Failed requests still present (~14-20/s) because the circuit breaker rejects requests while the circuit is open, but the system **does not crash**.

---

## Findings

| Metric | Before circuit breaker | After circuit breaker |
|---|---|---|
| Pod restarts during test | 6 | 0 (new) |
| 5xx errors | hidden (pod crash) | 0 |
| System remains stable | No | Yes |
| p95 latency (Overview) | ~2.01s | ~1.46s |
| k6 p99 latency | >4s | ~15ms |

- Circuit breaker prevents accumulation of blocked connections
- Gateway no longer crashes — instead of crashing, it returns 503 while the circuit is open
- System remains **partially available** even under maximum load

## Conclusion

**Hypothesis confirmed.** The circuit breaker eliminates cascading failure. The system passes the stress test without new pod crashes. However, during this test a new hidden weakness was discovered: httpx calls were synchronous inside async functions, blocking the event loop. That weakness did not cause a crash here, but manifested in later tests. _(See: Load-Test-Without-Async)_
