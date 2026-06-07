🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# Load Test — Otkriće blokiranog event loop-a (bez async fixa)

**Datum:** 07.06.2026.  
**Tip:** Incident — otkriven tokom rutinskog load testa  
**Target:** api-gateway  
**Alat:** k6  

---

## Kontekst

Nakon što je circuit breaker uspešno implementiran i verifikovan (vidi `API-GW-After-Circuit-Breaker`), pokrenut je novi load test u pripremi za "After" chaos eksperimente. Tokom ovog testa otkrivena je nova, skrivena slabost u implementaciji circuit breaker-a.

---

## Hipoteza

api-gateway sa circuit breaker-om i 5s timeoutovima stabilno podnosi load od 15 VUs tokom dužeg perioda.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 15 VUs |
| Trajanje | 55 min (planirano) |
| Circuit breaker | Da (pybreaker, fail_max=5, reset_timeout=30s) |
| httpx timeout | 5s |
| httpx pozivi | Sinhroni (`httpx.get()`) unutar async funkcija ⚠️ |

---

## Snimci ekrana

**k6 Load Test panel — oscilirajući request rate:**

![](<Screenshot from 2026-06-07 00-19-37.png>)

> 15 VUs. `::browse` request rate oscilira i pada u intervalima — direktna posledica restart ciklusa gatewaya. Failed requests **~10-15 req/s** kontinuirano. k6 p99 latency relativno nizak (~1ms) jer uspešni zahtevi prolaze brzo, ali mnogi ne prolaze uopšte.

---

**CPU i memorija po podu:**

![](<Screenshot from 2026-06-07 00-19-57.png>)

> api-gateway CPU **skače na 0.2 core-a (200m limit!)** čim primi saobraćaj. CPU throttling sprečava event loop da pravovremeno odgovori na liveness probu. Vidljivi padovi CPU/memorije na 0 u intervalima — to su momenti pada i restarta poda.

---

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 00-20-20.png>)

> Ukupni sistem izgleda relativno zdrav (13.8 req/s, p95 11.5ms, 0% stopa grešaka) jer Bookstore Overview gleda sve servise zajedno — restarti api-gatewaya se gube u šumu ostalih zdravih servisa.

---

**api-gateway Service Detail — 9 restarta:**

![](<Screenshot from 2026-06-07 00-20-34.png>)

> api-gateway: **9 pod restarta** za ~30 minuta load testa. p95 latency **159ms** — viši nego što je očekivano. Exit Code za sve restarте: **0** (graceful shutdown), ne crash — Kubernetes šalje SIGTERM jer liveness proba ne odgovori u roku.

---

**Pod Count — višestruki padovi:**

![](<Screenshot from 2026-06-07 00-20-54.png>)

> Pod Count pada na 0 **4-5 puta**. CPU usage skače na 0.2 core-a čim pod postane aktivan, pa pada na 0 pri restartu. Memorija stabilna (~48-64 MiB) — **nije OOM**, nego CPU throttling + blokada event loop-a.

---

## Analiza uzroka

Kombinacija dva problema:

### Problem 1 — Sinhroni httpx blokira event loop

```python
# ❌ Pogrešno — blokira event loop
@app.get("/books")
async def proxy_list_books():
    @book_breaker
    def call():
        return httpx.get(f"{BOOK_SERVICE_URL}/books", timeout=TIMEOUT)
    r = call()  # sinhron poziv u async funkciji!
```

FastAPI radi na asyncio event loop-u. Sinhroni `httpx.get()` blokira ceo event loop dok čeka odgovor. Dok je loop blokiran, ni jedan drugi zahtev — uključujući `/health` liveness probu — ne može biti opslužen.

### Problem 2 — CPU limit i probe timeout su prekratki

- CPU limit: **200m** (0.2 core-a) — premalo za Python + FastAPI + pybreaker + OpenTelemetry pod opterećenjem
- Liveness probe timeout: **1s** — pri CPU throttlingu, čak i neblokiran `/health` može kasniti >1s
- 3 uzastopna neuspeha probe → Kubernetes šalje SIGTERM → pod izlazi uredno (Exit Code 0)

---

## Primenjena rešenja

### Fix 1 — asyncio.to_thread() za httpx pozive

```python
# ✅ Ispravno — httpx radi u thread pool-u, event loop slobodan
async def _call(breaker, fn):
    try:
        return await asyncio.to_thread(breaker(fn))
    except pybreaker.CircuitBreakerError:
        return None
```

`asyncio.to_thread()` izvršava sinhronu funkciju u ThreadPoolExecutor-u bez blokiranja event loop-a. `/health` endpoint ostaje dostupan čak i pod punim opterećenjem.

### Fix 2 — Povećani resursi i probe timeout za api-gateway

```yaml
# deploy/overlays/kind/kustomization.yaml
resources:
  requests: { cpu: 100m, memory: 128Mi }
  limits:   { cpu: 500m, memory: 256Mi }   # 200m → 500m CPU
livenessProbe:
  timeoutSeconds: 5    # 1s → 5s
readinessProbe:
  timeoutSeconds: 5    # 1s → 5s
```

---

## Nalazi

- **Sinhroni I/O u async kodu** je skrivena, teško uočljiva slabost — sistem radi pod malim opterećenjem, ali pada pod realnim loadom
- Exit Code 0 i "Reason: Completed" u kubectl opisu su ključni pokazatelji: pod nije crashovao, **ubio ga je** Kubernetes zbog probe timeoutova
- CPU throttling na 200m je bio okidač problema — bez njega event loop bi možda stigao da odgovori probi na vreme
- Ovo je primer slabosti koja **ne bi bila otkrivena bez load testa** — u dev okruženju sa 1-2 korisnika sve funkcioniše normalno

## Zaključak

**Hipoteza oborena.** Otkrivena nova slabost uprkos prethodnom "uspešnom" circuit breaker testu. Demonstrira ključni princip chaos engineeringa: **svaki round testiranja može otkriti novi sloj problema**. Fix: asyncio.to_thread + povećani CPU limit + duži probe timeout. Verifikacija u sledećem testu _(vidi: Load-Test-With-Async)_.
