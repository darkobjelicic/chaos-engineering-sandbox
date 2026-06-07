[🇷🇸 Srpski](experiment.md) | 🇬🇧 English

# CPU Stress — inventory-service (80% load)

**Date:** 07.06.2026.  
**Type:** Chaos experiment — StressChaos  
**Target:** inventory-service  
**Tool:** Chaos Mesh + k6  

---

## Hypothesis

Artificial CPU load on the inventory service will cause increased latency on that service that will propagate to the api-gateway, but the system will remain functional without errors or pod crashes.

---

## Configuration

| Parameter | Value |
|---|---|
| Virtual users | 15 VUs |
| Chaos type | StressChaos — CPU |
| CPU load | 80% (2 workers) |
| Duration | 2 minutes |
| Circuit breaker | Yes |
| Probe timeout | 5s |

**Note:** The Grafana pod restarted during the experiment due to memory pressure after 16 hours of cluster uptime — only the start annotation line (~15:13) is visible, not the end.

---

## Screenshots

**inventory-service dashboard:**

![](<Screenshot from 2026-06-07 15-20-25.png>)

> inventory-service: 9.92 req/s, p95 **6.60ms**, error rate **0%**, restarts **0**. Latency spikes sharply during the chaos experiment — p99 reaches **~400ms**. CPU usage spikes to ~0.2 cores reaching the limit. Memory stays stable at ~72-76 MiB.

---

**api-gateway dashboard:**

![](<Screenshot from 2026-06-07 15-20-31.png>)

> api-gateway: 16.1 req/s, p95 **679ms**, error rate **0%**, restarts **0**. Latency propagated upward — the gateway waits for a response from the slow inventory-service but does not crash. Circuit breaker did not trip because there are no errors, only slowness.

---

**book-service (control):**

![](<Screenshot from 2026-06-07 15-20-46.png>)

> book-service: 18.8 req/s, p95 **9.13ms**, 0 restarts — minimally affected. CPU stress is isolated to inventory-service and did not spread.

---

**order-service (control):**

![](<Screenshot from 2026-06-07 15-21-09.png>)

> order-service: 4.30 req/s, p95 **210ms**, 0 restarts — slightly increased latency but no errors.

---

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 15-21-18.png>)

> Overall system: **54.3 req/s**, p95 **133ms**, error rate **0%**, active pods **12**. Only one annotation line visible (chaos experiment start) because Grafana crashed during recording.

---

**CPU and memory per pod:**

![](<Screenshot from 2026-06-07 15-21-31.png>)

> CPU usage on inventory service (red line) spikes to **~25%** at the moment of the chaos event. All other services stable — failure remained isolated to one pod.

---

**k6 Load Test:**

![](<Screenshot from 2026-06-07 15-21-41.png>)

> 15 VUs (ramp-down visible as load test was finishing). Failed requests: **~1 req/s** briefly then immediately drops to 0. Browse ~20-25 req/s stable, order ~2 req/s. p99 latency stays below **1.8ms** — k6 practically does not notice the chaos.

---

## Findings

- CPU stress on inventory service causes **latency spike up to ~400ms p99** on that service
- Latency propagates to the api-gateway (**679ms p95**) because the gateway waits for a response from the slow inventory-service
- Circuit breaker **did not trip** — no errors, only slowness. This is an important difference from the HTTP 500 scenario: the circuit breaker protects against errors, but not against a slow service
- **0 pod restarts**, **0 failed requests** (practically) — the system remains fully functional
- Isolation confirmed — book-service (~9ms) and other services were not affected
- Grafana pod restarted during the experiment due to memory pressure — the observability infrastructure itself is a potential weakness under prolonged operation

## Conclusion

**Hypothesis confirmed.** CPU stress causes performance degradation through increased latency, but not a system failure. Key finding: **the circuit breaker does not protect against a slow service, only against a service that returns errors**. Protection against a slow downstream service is the httpx 5s timeout which would, if latency exceeded that threshold, convert slowness into an error and trigger the circuit breaker.
