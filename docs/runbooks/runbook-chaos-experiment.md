🇷🇸 Srpski | [🇬🇧 English](runbook-chaos-experiment.en.md)

# Runbook: Pokretanje chaos eksperimenta

## Preduslovi

- kind klaster pokrenut (`kind get clusters` → `chaos-sandbox`)
- Svi podovi Running (`kubectl get pods -n bookstore`)
- Grafana dostupna (`http://grafana.monitoring.local`)

---

## Procedura

### 1. Pokreni load test (u zasebnom terminalu)

```bash
# Standardni load test za chaos eksperimente
make load VUS=15 DURATION=55m

# Ili stress test za kapacitivne testove
make stress VUS=50 DURATION=10m
```

Sačekaj **7-10 minuta** dok se ne uspostavi stabilan saobraćaj u Grafani (Bookstore Overview → Request Rate ravna linija).

### 2. Pokreni chaos eksperiment

```bash
make chaos-run EXPERIMENT=<ime-eksperimenta>
```

Dostupni eksperimenti:

| Eksperiment | Target | Trajanje | Tip |
|---|---|---|---|
| `network-latency-bookdb` | book-service DB | 2 min | NetworkChaos delay |
| `pod-failure-order` | order-service | 2 min | PodChaos |
| `http-500-order` | order-service | 2 min | HTTPChaos |
| `http-400-auth` | auth-service | 2 min | HTTPChaos |
| `cpu-stress-inventory` | inventory-service | 2 min | StressChaos |
| `rabbitmq-partition` | RabbitMQ | 1 min | NetworkChaos partition |

Skript automatski:
- Anotira početak i kraj u Grafani (crvene isprekidane linije)
- Primenjuje YAML
- Čeka trajanje chaos eksperimenta
- Briše eksperiment (zaustavlja haos)

### 3. Snimaj Grafanu tokom eksperimenta

Dashboardi koje treba pratiti:

| Dashboard | Šta gledati |
|---|---|
| **Service Detail** (target servis) | Pod Count, restarti, p95 latency |
| **Service Detail** (api-gateway) | Restarti = 0, stopa 5xx grešaka |
| **Bookstore Overview** | Stopa grešaka, aktivni podovi, saobraćaj |
| **Bookstore Overview** → Errors & Health | 5xx / 4xx stopa po servisu |
| **Bookstore Overview** → Load Test (k6) | Failed requests, VUs, p99 latency |
| **Bookstore Overview** → CPU & Memory | CPU spike na target podu |

### 4. Proveri cleanup

```bash
kubectl get httpchaos,podchaos,networkchaos,stresschaos -n bookstore
```

Ako je ostao aktivan resource nakon eksperimenta:
```bash
kubectl delete httpchaos,podchaos,networkchaos,stresschaos --all -n bookstore
```

---

## Poznati problemi

**HTTPChaos sa `path: "*"` pogađa `/health` endpoint**
- Simptom: target servis ima mnoštvo restarta tokom HTTP chaos eksperimenta
- Fix: koristiti specifičan path (npr. `/orders*`, `/auth*`)

**Chaos resource ostao aktivan (eksperiment se nije počistio)**
- Simptom: servis nastavlja da se ponaša haotično i nakon završetka eksperimenta
- Dijagnoza: `kubectl get httpchaos,podchaos -n bookstore`
- Fix: `kubectl delete -f chaos/experiments/<ime>.yaml`

**CrashLoopBackOff na servisu nakon chaos eksperimenta**
- Uzrok: exponential backoff — Kubernetes čeka između restarta
- Fix: `kubectl delete pod -n bookstore -l app=<servis>` da resetuješ backoff
