🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# API Gateway Fine Tuning — Iterativno otkrivanje i otklanjanje slabosti

**Period:** 25.05.2026. – 07.06.2026.  
**Target:** api-gateway  
**Tip:** Iterativni load test + hardening  

---

## Pregled

Ovo nije jedan eksperiment nego **četiri iteracije** istog stress testa, od kojih je svaka otkrila novi sloj slabosti. Prikazuje kako chaos engineering funkcioniše u praksi — ne kao jednokratna provera, nego kao kontinuirani ciklus poboljšanja.

```
Iteracija 1  →  Iteracija 2  →  Iteracija 3  →  Iteracija 4
Pre CB          Posle CB         Otkrivena        Posle asyncio
                                 event loop        + resource fix
                                 blokada
```

---

## Iteracija 1 — Polazna tačka: gateway pada pod opterećenjem

**Datum:** 25.05.2026. | **Folder:** `API-GW-Before-Circuit-Breaker/`

**Podešavanja:** 50 VUs, httpx bez timeoutova, bez circuit breaker-a.

![](<../API-GW-Before-Circuit-Breaker/Screenshot from 2026-05-25 22-58-33.png>)

> **6 pod restarta**, p95 latency 4-5s. httpx pozivi bez timeoutova akumuliraju konekcije dok ne iscrpe resurse. Klasičan kaskadni kvar.

**Hipoteza oborena.** Identifikovana potreba za circuit breaker-om i HTTP timeoutovima.

**Primenjena promena:**
- Dodat `pybreaker==1.0.2`
- Circuit breaker po servisu: `fail_max=5, reset_timeout=30s`
- httpx timeout: `5s` na svim pozivima

---

## Iteracija 2 — Posle circuit breaker-a: stabilniji, ali...

**Datum:** 26.05.2026. | **Folder:** `API-GW-After-Circuit-Breaker/`

**Podešavanja:** 50 VUs, circuit breaker aktivan.

![](<../API-GW-After-Circuit-Breaker/Screenshot from 2026-05-26 19-47-59.png>)

> **0 novih restarta**, 0 5xx grešaka, p95 1.46s. Circuit breaker eliminiše kaskadni kvar. Sistem prolazi stress test.

**Hipoteza potvrđena.** Ali implementacija ima skrivenu grešku koja se ispoljava tek pri dužem radu.

---

## Iteracija 3 — Otkriće: sinhroni httpx blokira event loop

**Datum:** 07.06.2026. | **Folder:** `Load-Test-Without-Async/`

**Podešavanja:** 15 VUs, duži load test, circuit breaker aktivan.

![](<../Load-Test-Without-Async/Screenshot from 2026-06-07 00-20-34.png>)

> **9 pod restarta** za 30 minuta. Exit Code 0 — Kubernetes šalje SIGTERM jer liveness proba ne odgovara. Root cause: sinhroni `httpx.get()` unutar `async` funkcija blokira event loop pa `/health` ne može da odgovori u roku.

```python
# Pogrešno — blokira event loop
async def proxy_list_books():
    @book_breaker
    def call():
        return httpx.get(f"{BOOK_SERVICE_URL}/books", timeout=TIMEOUT)
    r = call()  # sinhron poziv blokira ceo event loop!
```

**Kombinacija problema:**
1. Sinhroni httpx u async funkcijama → event loop blokiran
2. CPU limit 200m → Python pod opterećenjem ne stigne da odgovori probi
3. Liveness probe timeout 1s → prekratko za Python pod pritiskom

**Primenjena promena:**
```python
# Ispravno — thread pool, event loop slobodan
async def _call(breaker, fn):
    try:
        return await asyncio.to_thread(breaker(fn))
    except pybreaker.CircuitBreakerError:
        return None
```
- `asyncio.to_thread()` za sve httpx pozive
- CPU limit: `200m → 500m`
- Probe timeout: `1s → 5s`

---

## Iteracija 4 — Verifikacija: stabilan sistem

**Datum:** 07.06.2026. | **Folder:** `Load-Test-With-Async/`

**Podešavanja:** 15 VUs, 55 min sustained load.

![](<../Load-Test-With-Async/Screenshot from 2026-06-07 13-34-38.png>)

> **Restarti = 0**, **Failed requests = 0**, CPU stabilan na ~40%, Pod Count = 1 kroz ceo test.

![](<../Load-Test-With-Async/Screenshot from 2026-06-07 13-33-20.png>)

> k6: 0 neuspešnih zahteva tokom 55 minuta. Browse ~25-30 req/s, order ~2-3 req/s. p99 ~1.5ms.

**Hipoteza potvrđena.** Sistem stabilan pod sustained opterećenjem.

---

## Evolucija kroz iteracije

| Metrika | Iter. 1 | Iter. 2 | Iter. 3 | Iter. 4 |
|---|---|---|---|---|
| VUs | 50 | 50 | 15 | 15 |
| Pod restarti | **6** | 0 | **9** | **0** |
| k6 Failed req/s | ~14 | ~14-20 | ~10-15 | **0** |
| 5xx greške | Skrivene | 0 | 0 | **0** |
| Sistem stabilan | Ne | Da* | Ne | **Da** |
| Exit code pada | — | — | 0 (SIGTERM) | — |

*Stabilan ali sa skrivenom greškom u kodu

---

## Naučene lekcije

1. **Circuit breaker nije dovoljan** — implementacija mora biti async-ispravna. Dodavanje sinhrne biblioteke u async kod unosi suptilne greške koje se ne vide pod malim opterećenjem.

2. **Probe timeout mora da odgovara karakteristikama aplikacije** — 1s je premalo za Python aplikaciju pod CPU opterećenjem. Timeout treba da bude manji od `httpx_timeout` ali dovoljno velik za normalnu latency.

3. **CPU limit je deo SLA** — premalo CPU = throttling = health check timeoutovi = nepotrebni restarti. Resource limits moraju biti kalibrisani prema stvarnom opterećenju.

4. **Chaos engineering je iterativan** — svaki round testiranja može otkriti novi sloj problema koji prethodni nije pokazao.
