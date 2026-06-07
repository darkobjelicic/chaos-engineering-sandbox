🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# HTTP 500 injekcija — order-service (posle circuit breaker-a + async fixa)

**Datum:** 07.06.2026.  
**Tip:** Chaos eksperiment — HTTPChaos  
**Target:** order-service  
**Alat:** Chaos Mesh + k6  

---

## Kontekst

Isti eksperiment kao `http-500-order-Before-Circuit-Breaker`, pokrenut nakon implementacije circuit breaker-a i asyncio.to_thread fixa. Cilj je da se verifikuje da api-gateway više ne pada kada downstream servis vraća greške.

**Napomena:** Tokom ovog eksperimenta otkriven je dodatni problem — Chaos Mesh konfiguracija koristi `path: "*"` što uključuje i `/health` endpoint. Liveness proba na order-service dobija 500 odgovor i Kubernetes restartuje pod. Liveness probe timeout od 1s dodatno pogoršava situaciju pod opterećenjem. Fix (timeout 1s → 5s za sve servise) primenjen nakon ovog testa.

---

## Hipoteza

Circuit breaker na api-gatewayu sprečiće kaskadni kvar — api-gateway neće padati kada order-service vraća HTTP 500 greške.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 15 VUs |
| Tip haosa | HTTPChaos — replace response code |
| Injektovana greška | HTTP 500 na sve odgovore (path: "*") |
| Trajanje | 2 minuta |
| Circuit breaker | Da (fail_max=5, reset_timeout=30s) |
| Liveness probe timeout | 1s (nije još popravljeno) |

---

## Snimci ekrana

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 14-39-19.png>)

> Ukupni sistem: 46.6 req/s, p95 **79.6ms**, stopa grešaka **5.14%**, aktivnih podova **11** (order-service se restartuje). Chaos eksperiment vidljiv na ~14:30. api-gateway latency kratko skače ali sistem ne pada.

---

**Errors & Health:**

![](<Screenshot from 2026-06-07 14-39-33.png>)

> api-gateway 5xx stopa grešaka raste na **~12.5%** — to su 503 odgovori koje circuit breaker vraća dok je kolo otvoreno. order-service 4xx stopa dostiže **~80%** (Chaos Mesh injektuje 500 na sve pathove). Active HTTP requests ostaju na max **3** — nema nakupljanja konekcija.

---

**CPU i memorija:**

![](<Screenshot from 2026-06-07 14-39-42.png>)

> api-gateway CPU stabilan na ~40% kroz ceo test. order-service CPU pada tokom restarta. Ostali servisi potpuno nepogođeni.

---

**k6 Load Test:**

![](<Screenshot from 2026-06-07 14-39-51.png>)

> 15 VUs. Failed requests dostižu **~2 req/s** u trenutku chaos eksperimenta — isto kao kod pod-failure eksperimenta. Browse operacije ostaju stabilne (~25-30 req/s). p99 latency ostaje ispod **1.5ms**.

---

**order-service dashboard:**

![](<Screenshot from 2026-06-07 14-40-05.png>)

> order-service: request rate pada na **0 req/s** tokom chaos eksperimenta, **9 pod restarta** — Chaos Mesh injektuje 500 i na `/health` endpoint pa liveness proba failuje. Ovo je direktna motivacija za popravku probe timeout-a na svim servisima.

---

**api-gateway dashboard — ključni snimak:**

![](<Screenshot from 2026-06-07 14-40-14.png>)

> api-gateway: 24.9 req/s, p95 **201ms**, stopa 5xx grešaka **13.2%**, restarti **= 0**. api-gateway NE PADA. 5xx greške su 503 odgovori circuit breaker-a — vidljive i kontrolisane, ne skrivene iza pada poda kao u prethodnom scenariju.

---

**notification-service (provera izolacije):**

![](<Screenshot from 2026-06-07 14-40-22.png>)

> notification-service: **0 restarta**, p95 **4.75ms** — potpuno stabilan.

---

## Poređenje pre i posle

| Metrika | Pre (bez CB) | Posle (CB + async) |
|---|---|---|
| api-gateway restarti | **6** | **0** |
| order-service restarti | 8 | 9* |
| api-gateway 5xx | Skrivene (pad poda) | **13.2% (503 od CB)** |
| order-service 4xx | ~55% | **~80%** |
| k6 Failed requests (peak) | Visoko, kontinuirano | **~2 req/s, kratkotrajno** |
| Active HTTP requests | Nakupljaju se | **Max 3** |
| api-gateway stabilan | Ne | **Da** |
| Greške vidljive u metrikama | Ne | **Da** |

*order-service ima više restarta jer Chaos Mesh pogađa i `/health` — uzrok otklonjen povećanjem probe timeout-a na 5s za sve servise.

---

## Nalazi

- **api-gateway ne pada** (0 restarta) — circuit breaker uspešno izoluje greške
- 5xx greške (13.2%) su sada **vidljive i očekivane** — circuit breaker vraća 503 umesto da gateway padne. Ovo je poboljšanje observabilnosti: u prethodnom scenariju greške su bile skrivene iza pada poda
- order-service se restartuje zbog Chaos Mesh konfiguracije (`path: "*"`) koja pogađa i liveness probu — napomena za buduće eksperimente: koristiti specifičniji path (npr. `/orders*`)
- Active HTTP requests ostaju minimalni — nema thundering herd efekta

## Zaključak

**Hipoteza potvrđena.** Circuit breaker eliminiše kaskadni kvar. api-gateway ostaje stabilan bez obzira na greške downstream servisa. Otkrivena dva sporedna problema:
1. `path: "*"` u HTTPChaos konfiguraciji pogađa health endpointe — koristiti specifičniji path u budućim eksperimentima
2. Liveness probe timeout od 1s je prekratak za sve Python servise — **popravljeno** povećanjem na 5s u kustomization overlay-u
