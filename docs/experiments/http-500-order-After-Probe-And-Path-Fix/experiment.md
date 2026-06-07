🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# HTTP 500 injekcija — order-service (posle popravke probe + path konfiguracije)

**Datum:** 07.06.2026.  
**Tip:** Chaos eksperiment — HTTPChaos (Iteracija 3)  
**Target:** order-service  
**Alat:** Chaos Mesh + k6  

---

## Kontekst

Treća iteracija HTTP 500 eksperimenta. Pored circuit breaker-a i asyncio fixa, primenjena su još dva poboljšanja otkrivena u prethodnoj iteraciji:

1. **Chaos path sužen** — `path: "*"` → `path: "/orders*"` da `/health` endpoint ne bude pogođen
2. **Probe timeout povećan** — 1s → 5s za sve Python servise

Ovo je finalna verifikacija da sistem ispravno rukuje HTTP 500 greškama bez nuspojava.

---

## Hipoteza

Sa svim primenjenim popravkama, sistem će podneti HTTP 500 greške na order-service bez ijednog pod restarta (ni api-gateway ni order-service) i uz minimalne neuspešne zahteve.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 15 VUs |
| Tip haosa | HTTPChaos — replace response code |
| Injektovana greška | HTTP 500 samo na `/orders*` |
| Trajanje | 2 minuta |
| Circuit breaker | Da (fail_max=5, reset_timeout=30s) |
| Probe timeout | 5s (svi servisi) |

---

## Snimci ekrana

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 15-10-23.png>)

> Ukupni sistem: **56.5 req/s**, p95 **149ms**, stopa grešaka **0%**, aktivnih podova **12**. Kratki latency spike na api-gatewayu tokom chaos eksperimenta (~15:03), ali sistem nikada ne gubi stabilnost.

---

**Errors & Health:**

![](<Screenshot from 2026-06-07 15-10-36.png>)

> api-gateway 5xx stopa grešaka dostiže **~14%** kratko dok circuit breaker otvara kolo, pa odmah pada na **0%**. Nema 4xx grešaka. Active HTTP requests ostaju normalni — nema nakupljanja konekcija.

---

**CPU i memorija:**

![](<Screenshot from 2026-06-07 15-10-45.png>)

> Svi servisi stabilni. Nema dramatičnih padova CPU/memorije koji bi ukazivali na restart cikluse.

---

**k6 Load Test:**

![](<Screenshot from 2026-06-07 15-10-57.png>)

> 15 VUs. Failed requests dostižu **~6 req/s** kratko tokom chaos eksperimenta pa odmah padaju na 0. Browse operacije (~20-25 req/s) minimalno pogođene. p99 latency ostaje ispod **2ms**.

---

**order-service — ključni snimak:**

![](<Screenshot from 2026-06-07 15-11-09.png>)

> order-service: 2.46 req/s, p95 **159ms**, stopa grešaka **0%**, restarti **= 0**. Pod Count stabilan na 1 tokom celog testa. Direktna potvrda da path fix (`/orders*`) štiti `/health` endpoint od injekcije haosa.

---

**api-gateway:**

![](<Screenshot from 2026-06-07 15-11-16.png>)

> api-gateway: 17.8 req/s, p95 **231ms**, stopa 5xx grešaka **0%** (posle chaos eksperimenta), restarti **= 0**. Circuit breaker odradi posao i vrati se u normalno stanje.

---

**notification-service (provera izolacije):**

![](<Screenshot from 2026-06-07 15-11-24.png>)

> notification-service: **0 restarta**, p95 **4.75ms** — potpuno stabilan.

---

## Evolucija kroz tri iteracije

| Metrika | Iteracija 1 (pre CB) | Iteracija 2 (CB + async) | Iteracija 3 (+ probe + path) |
|---|---|---|---|
| api-gateway restarti | **6** | 0 | **0** |
| order-service restarti | 8 | **9** | **0** |
| k6 Failed req (peak) | Visoko, kontinuirano | ~2 req/s | **~6 req/s kratko** |
| Aktivnih podova | 10-11 | 11 | **12** |
| Stopa grešaka ukupno | Skrivene | 5.14% | **0%** |
| Sistem stabilan | Ne | Delimično | **Da** |
| Chaos pogađa /health | — | Da | **Ne** |

*Napomena: Failed requests u Iteraciji 3 (~6/s) viši od Iteracije 2 (~2/s) jer circuit breaker sada može normalno da odbija i vraća 503 bez pada poda — greške su kontrolisane i vidljive, ne skrivene iza restarta.

---

## Nalazi

- **0 restarta** na svim servisima — sistem se ponaša tačno kako je projektovan
- "Malo toga se desilo" je **dokaz uspeha** — cilj chaos engineeringa nije da sistem ne oseti kvar, nego da ga podnese bez kolapsa
- Circuit breaker otvara kolo, vraća 503 klijentima, čeka reset_timeout (30s), proba ponovo — sve po specifikaciji
- Specifičnost path-a u chaos eksperimentima je ključna — `path: "*"` je previše agresivan za Python servise sa kratkim probe timeout-ovima

## Zaključak

**Hipoteza potvrđena.** Finalna iteracija demonstrira sistem koji ispravno i predvidivo rukuje greškama downstream servisa. Svaka od tri iteracije otkrila je novi sloj poboljšanja, što je suština chaos engineering metodologije.
