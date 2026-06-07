[🇷🇸 Srpski](README.md) | 🇬🇧 English

# Chaos Experiments — Overview

All experiments follow a hypothesis-driven methodology:  
**Define steady state → form hypothesis → inject failure → observe → conclude**

---

## API Gateway Fine Tuning

Four load test iterations that progressively uncovered and eliminated weaknesses in the api-gateway. The most important part of the project — demonstrates how chaos engineering works in practice.

| Iteration | Description | Result |
|---|---|---|
| [Before circuit breaker](API-GW-Before-Circuit-Breaker/experiment.md) | 50 VUs, no protection | 6 pod restarts, cascading failure |
| [After circuit breaker](API-GW-After-Circuit-Breaker/experiment.md) | pybreaker + 5s timeout | 0 restarts, but hidden bug remained |
| [Event loop blocking discovered](Load-Test-Without-Async/experiment.md) | sync httpx in async code | 9 restarts @ 15 VUs (SIGTERM) |
| [After asyncio fix](Load-Test-With-Async/experiment.md) | asyncio.to_thread + CPU 500m + probe 5s | 0 restarts, 0 failed requests |

Combined narrative across all four iterations: [API-GW-Fine-Tuning/experiment.md](API-GW-Fine-Tuning/experiment.md)

---

## Network Latency — book-service Database

300ms latency injection between book-service and PostgreSQL.

| Experiment | Link | Key Finding |
|---|---|---|
| Before fix | [experiment.md](network-latency-bookdb-Before-Circuit-Breaker/experiment.md) | DB connection pool reached 75%, latency propagated to clients |
| After fix | [experiment.md](network-latency-bookdb-After-Circuit-Breaker-And-With-Async/experiment.md) | 0 restarts, 0 errors — clean degradation instead of chaotic crash |

---

## Pod Failure — order-service

Killing the order-service pod and observing system recovery.

| Experiment | Link | Key Finding |
|---|---|---|
| Before fix | [experiment.md](pod-failure-order-Before-Circuit-Breaker/experiment.md) | 3 restarts, ~14 failed req/s, api-gateway unstable |
| After fix | [experiment.md](pod-failure-order-After-Circuit-Breaker-And-With-Async/experiment.md) | 0 api-gateway restarts, ~2 failed req/s, fast recovery |

---

## HTTP 500 Injection — order-service (3 iterations)

Injecting HTTP 500 errors on order-service responses. Three iterations, each revealing a new problem.

| Iteration | Link | Key Finding |
|---|---|---|
| Before circuit breaker | [experiment.md](http-500-order-Before-Circuit-Breaker/experiment.md) | 6 api-gateway restarts, thundering herd |
| After CB + async (path: *) | [experiment.md](http-500-order-After-Circuit-Breaker-And-With-Async/experiment.md) | 0 api-gateway restarts, but 9 order-service restarts (path: * hits /health) |
| After probe + path fix | [experiment.md](http-500-order-After-Probe-And-Path-Fix/experiment.md) | 0 restarts, system stable, "nothing happened" = proof of success |

---

## CPU Stress — inventory-service

80% CPU load on inventory-service with 2 workers.

| Experiment | Link | Key Finding |
|---|---|---|
| CPU stress 80% | [experiment.md](cpu-80-inventory/experiment.md) | Latency propagates, 0 errors — circuit breaker does not protect against a slow service |

---

## All Experiments Summary

| Experiment | Target | Before | After |
|---|---|---|---|
| Stress test | api-gateway | 6 restarts, cascading failure | 0 restarts, CB isolates errors |
| Network latency (300ms DB) | book-service | Pool 75%, degraded | Stable, 0 errors |
| Pod failure | order-service | ~14 failed req/s | ~2 failed req/s, fast recovery |
| HTTP 500 (path: *) | order-service | 6+8 restarts | 0 GW restarts, 9 OS restarts* |
| HTTP 500 (path: /orders*) | order-service | — | 0 restarts, system stable |
| CPU stress 80% | inventory-service | — | Latency +400ms p99, 0 errors |

*path: `*` hit the `/health` endpoint — fixed in the third iteration
