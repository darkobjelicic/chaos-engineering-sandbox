🇷🇸 Srpski | [🇬🇧 English](ADR-002-asyncio-thread-pool.en.md)

# ADR-002: asyncio.to_thread za httpx pozive u api-gateway

**Status:** Prihvaćeno  
**Datum:** 07.06.2026.  

---

## Kontekst

Nakon implementacije circuit breaker-a (ADR-001), load test pod 15 VUs pokazao je da api-gateway nastavlja da pada — ali na drugačiji način. Exit Code je bio 0 (graceful shutdown), ne crash, što je ukazivalo da Kubernetes šalje SIGTERM zbog liveness probe timeoutova.

Analiza uzroka:

```python
# Problematičan kod — sinhroni httpx unutar async funkcije
async def proxy_list_books():
    @book_breaker
    def call():
        return httpx.get(f"{BOOK_SERVICE_URL}/books", timeout=TIMEOUT)
    r = call()  # blokira asyncio event loop!
```

FastAPI koristi asyncio event loop. Sinhroni `httpx.get()` poziv blokira ceo event loop dok čeka HTTP odgovor. Za to vreme, ni jedan drugi korutinski zadatak ne može da se izvrši — uključujući liveness probe endpoint `/health`. Kubernetes proba failuje 3 puta (3 × 1s timeout = 3s) i šalje SIGTERM, pod se gasi uredno (Exit Code 0).

Ovo se nije pojavilo u početnim testovima jer je 50 VUs kratkotrajna sesija. Sa 15 VUs i dugim sustained testom, throttling na 200m CPU + blokiran event loop = siguran fail.

---

## Odluka

Sve sinhrono httpx pozive izvršavati u **ThreadPoolExecutor-u** koristeći `asyncio.to_thread()`, čime se event loop oslobađa za ostale zadatke.

```python
async def _call(breaker, fn):
    try:
        return await asyncio.to_thread(breaker(fn))
    except pybreaker.CircuitBreakerError:
        return None
```

Istovremeno:
- CPU limit povećan: `200m → 500m`
- Liveness/readiness probe timeout: `1s → 5s` (za api-gateway i sve ostale Python servise)

---

## Razmatrane alternative

**A) Nativni async httpx (`httpx.AsyncClient`)**  
Čistije rešenje — `httpx.AsyncClient` nativno podržava `await`. Problem: `pybreaker` je sinhrona biblioteka i ne podržava async pozive. Zahteva zamenu `pybreaker` sa async-kompatibilnim circuit breaker rešenjem (npr. `aiobreaker`) ili pisanje sopstvene implementacije.

**B) asyncio.to_thread (odabrano)**  
Zadržava `pybreaker` i postojeću logiku, samo premešta sinhrne pozive u thread pool. Manji opseg promene, lakše za pregled. Threading overhead je zanemariv za I/O-bound rad.

**C) Povećanje CPU limita bez izmene koda**  
Moglo bi da smanji učestalost problema ali ne rešava uzrok — event loop bi i dalje bio blokiran, samo ređe.

---

## Posledice

- api-gateway stabilan pod sustained opterećenjem — 0 restarta tokom 55-minutnog testa sa 15 VUs
- k6 failed requests: 0 (vs ~10-15/s pre fixa)
- Threading overhead: zanemariv za I/O-bound operacije (HTTP pozivi)
- CPU koristi ~40% od 500m limita pod opterećenjem — ima prostora za rast
- Probe timeout od 5s uveden za sve Python servise jer isti problem može da pogodi bilo koji servis pod CPU pritiskom
