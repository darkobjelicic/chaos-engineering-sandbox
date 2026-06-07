🇷🇸 Srpski | [🇬🇧 English](runbook-api-gateway-crashloop.en.md)

# Runbook: api-gateway CrashLoopBackOff

## Simptomi

- `kubectl get pods -n bookstore` pokazuje `CrashLoopBackOff` ili česte restarте na `api-gateway`
- Grafana: Pod Count oscilira između 0 i 1
- k6 / korisnici: visok broj neuspešnih zahteva ili odbijenih konekcija

---

## Dijagnoza

### Korak 1 — Proveri exit code

```bash
kubectl describe pod -n bookstore -l app=api-gateway | grep -A5 "Last State:"
```

| Exit Code | Značenje | Sledeći korak |
|---|---|---|
| `0` + Reason: Completed | SIGTERM od Kubernetesa (probe fail) | → Korak 2 |
| `137` | OOMKilled | Povećaj memory limit |
| `1` / `2` | Greška aplikacije | → Korak 3 |

### Korak 2 — Proveri probe timeout (Exit Code 0)

```bash
kubectl describe pod -n bookstore -l app=api-gateway | grep -A3 "Liveness:"
```

Ako je `timeoutSeconds: 1` — timeout je prekratak. Pod opterećenjem, `/health` ne stigne da odgovori.

**Fix:** Povećaj u `deploy/overlays/kind/kustomization.yaml`:
```yaml
- op: replace
  path: /spec/template/spec/containers/0/livenessProbe/timeoutSeconds
  value: 5
```

Proveri i CPU limit — ako je pod throttlingom (~200m za Python), proba kasni:
```bash
kubectl top pod -n bookstore -l app=api-gateway
```

### Korak 3 — Proveri logove

```bash
kubectl logs -n bookstore -l app=api-gateway --previous | tail -50
```

Traži:
- `RuntimeError` / `Exception` — greška aplikacije, proveri kod
- `CircuitBreakerError` — circuit breaker otvoren, proveri downstream servise
- `httpx.ConnectError` — downstream servis nedostupan

### Korak 4 — Proveri downstream servise

```bash
kubectl get pods -n bookstore
```

Ako je neki downstream servis u CrashLoopBackOff — circuit breaker na api-gatewayu bi trebalo da zaštiti gateway. Ako ne štiti, proveri da li je circuit breaker konfigurisan.

---

## Brzi fix (privremeno)

Obriši pod da resetuješ backoff ciklus:
```bash
kubectl delete pod -n bookstore -l app=api-gateway
```

Kubernetes će kreirati novi pod odmah. Ovo ne rešava uzrok.

---

## Provera da je sve u redu

```bash
kubectl get pods -n bookstore -l app=api-gateway
# Očekivano: 1/1 Running, RESTARTS = 0

kubectl logs -n bookstore -l app=api-gateway | tail -5
# Očekivano: "Application startup complete."
```
