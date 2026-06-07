[🇷🇸 Srpski](runbook-chaos-experiment.md) | 🇬🇧 English

# Runbook: Running a Chaos Experiment

## Prerequisites

- kind cluster running (`kind get clusters` → `chaos-sandbox`)
- All pods Running (`kubectl get pods -n bookstore`)
- Grafana available (`http://grafana.monitoring.local`)

---

## Procedure

### 1. Start load test (in a separate terminal)

```bash
# Standard load test for chaos experiments
make load VUS=15 DURATION=55m

# Or stress test for capacity testing
make stress VUS=50 DURATION=10m
```

Wait **7-10 minutes** for stable traffic in Grafana (Bookstore Overview → Request Rate flat line).

### 2. Run chaos experiment

```bash
make chaos-run EXPERIMENT=<experiment-name>
```

Available experiments:

| Experiment | Target | Duration | Type |
|---|---|---|---|
| `network-latency-bookdb` | book-service DB | 2 min | NetworkChaos delay |
| `pod-failure-order` | order-service | 2 min | PodChaos |
| `http-500-order` | order-service | 2 min | HTTPChaos |
| `http-400-auth` | auth-service | 2 min | HTTPChaos |
| `cpu-stress-inventory` | inventory-service | 2 min | StressChaos |
| `rabbitmq-partition` | RabbitMQ | 1 min | NetworkChaos partition |

The script automatically:
- Annotates start and end in Grafana (red dashed lines)
- Applies the YAML
- Waits for the experiment duration
- Deletes the experiment (stops chaos)

### 3. Monitor Grafana during the experiment

Dashboards to watch:

| Dashboard | What to look for |
|---|---|
| **Service Detail** (target service) | Pod Count, restarts, p95 latency |
| **Service Detail** (api-gateway) | Restarts = 0, 5xx error rate |
| **Bookstore Overview** | Error rate, running pods, traffic |
| **Bookstore Overview** → Errors & Health | 5xx / 4xx rate per service |
| **Bookstore Overview** → Load Test (k6) | Failed requests, VUs, p99 latency |
| **Bookstore Overview** → CPU & Memory | CPU spike on target pod |

### 4. Verify cleanup

```bash
kubectl get httpchaos,podchaos,networkchaos,stresschaos -n bookstore
```

If a resource remained active after the experiment:
```bash
kubectl delete httpchaos,podchaos,networkchaos,stresschaos --all -n bookstore
```

---

## Known Issues

**HTTPChaos with `path: "*"` hits the `/health` endpoint**
- Symptom: target service has many restarts during HTTP chaos experiment
- Fix: use a specific path (e.g., `/orders*`, `/auth*`)

**Lingering chaos resource (experiment did not clean up)**
- Symptom: service continues chaotic behavior after experiment ends
- Diagnosis: `kubectl get httpchaos,podchaos -n bookstore`
- Fix: `kubectl delete -f chaos/experiments/<name>.yaml`

**CrashLoopBackOff on service after chaos experiment**
- Cause: exponential backoff — Kubernetes waits between restarts
- Fix: `kubectl delete pod -n bookstore -l app=<service>` to reset backoff
