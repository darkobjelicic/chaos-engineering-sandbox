[🇷🇸 Srpski](bookstore.md) | 🇬🇧 English

# Steady-State Definition — Bookstore

The steady-state describes how the system behaves under normal conditions — without active chaos experiments, under typical load. Every chaos experiment measures how far the system deviates from this state and whether it returns to it after the fault injection ends.

---

## Reference Load

Steady-state is measured with a **load test** (10 VUs, 25 minutes) that simulates realistic user flows:
- 70% of users browse books and inventory (`browse` group)
- 30% of users place orders (`order` group)

```bash
k6 run load-testing/k6/scripts/load.js
```

---

## HTTP Performance

| Metric | Threshold |
|---|---|
| Error rate (overall) | < 5% |
| p95 latency — browse (`/books`, `/inventory`) | < 500ms |
| p95 latency — order (`/orders`) | < 1500ms |
| p95 latency (overall) | < 1000ms |

These values match the k6 thresholds in `load.js` and represent acceptable system behavior under normal load.

---

## Cluster Health

Under normal conditions, all pods remain `Running` and `Ready` throughout the entire load test with zero restarts. CrashLoopBackOff should not appear on any pod.

```bash
kubectl get pods -n bookstore
```

---

## Circuit Breaker State

All four circuit breakers in api-gateway (book-service, order-service, auth-service, inventory-service) remain `CLOSED` throughout the load test. There are not enough errors to reach the threshold of 5 consecutive failures that would open a circuit.

---

## RabbitMQ

Communication between order-service and notification-service flows without interruption. Queue depth for `orders` stays below 100 messages — messages are consumed faster than they arrive.

```bash
kubectl exec -n bookstore deploy/rabbitmq -- rabbitmqctl list_queues name messages
```

---

## Recovery Time Objective

If a chaos experiment causes a deviation from the above state, the system is considered recovered when all metrics return within the defined thresholds **within 2 minutes** of the fault injection ending.
