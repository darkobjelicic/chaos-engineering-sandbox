[🇷🇸 Srpski](runbook-api-gateway-crashloop.md) | 🇬🇧 English

# Runbook: api-gateway CrashLoopBackOff

## Symptoms

- `kubectl get pods -n bookstore` shows `CrashLoopBackOff` or frequent restarts on `api-gateway`
- Grafana: Pod Count oscillates between 0 and 1
- k6 / users: high number of failed requests or rejected connections

---

## Diagnosis

### Step 1 — Check exit code

```bash
kubectl describe pod -n bookstore -l app=api-gateway | grep -A5 "Last State:"
```

| Exit Code | Meaning | Next step |
|---|---|---|
| `0` + Reason: Completed | SIGTERM from Kubernetes (probe fail) | → Step 2 |
| `137` | OOMKilled | Increase memory limit |
| `1` / `2` | Application error | → Step 3 |

### Step 2 — Check probe timeout (Exit Code 0)

```bash
kubectl describe pod -n bookstore -l app=api-gateway | grep -A3 "Liveness:"
```

If `timeoutSeconds: 1` — timeout is too short. Under load, `/health` cannot respond in time.

**Fix:** Increase in `deploy/overlays/kind/kustomization.yaml`:
```yaml
- op: replace
  path: /spec/template/spec/containers/0/livenessProbe/timeoutSeconds
  value: 5
```

Also check CPU limit — if the pod is being throttled (~200m for Python), probes will be delayed:
```bash
kubectl top pod -n bookstore -l app=api-gateway
```

### Step 3 — Check logs

```bash
kubectl logs -n bookstore -l app=api-gateway --previous | tail -50
```

Look for:
- `RuntimeError` / `Exception` — application error, check code
- `CircuitBreakerError` — circuit breaker open, check downstream services
- `httpx.ConnectError` — downstream service unavailable

### Step 4 — Check downstream services

```bash
kubectl get pods -n bookstore
```

If a downstream service is in CrashLoopBackOff — the circuit breaker on api-gateway should protect the gateway. If it does not, verify the circuit breaker is configured.

---

## Quick fix (temporary)

Delete the pod to reset the backoff cycle:
```bash
kubectl delete pod -n bookstore -l app=api-gateway
```

Kubernetes will create a new pod immediately. This does not fix the root cause.

---

## Verify everything is OK

```bash
kubectl get pods -n bookstore -l app=api-gateway
# Expected: 1/1 Running, RESTARTS = 0

kubectl logs -n bookstore -l app=api-gateway | tail -5
# Expected: "Application startup complete."
```
