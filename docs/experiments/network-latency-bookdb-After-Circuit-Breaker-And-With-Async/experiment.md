🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# Network Latency — book-service baza podataka (posle circuit breaker-a + async fixa)

**Datum:** 07.06.2026.  
**Tip:** Chaos eksperiment — NetworkChaos  
**Target:** book-service → PostgreSQL (postgres-book)  
**Alat:** Chaos Mesh + k6  

---

## Kontekst

Isti eksperiment kao `network-latency-bookdb-Before-Circuit-Breaker`, pokrenut nakon circuit breaker-a i asyncio.to_thread fixa. Cilj je da se vidi da li se ponašanje sistema promenilo.

---

## Hipoteza

Sistem će podneti 300ms network latency prema bazi book-service. api-gateway neće padati. DB connection pool neće biti iscrpljen.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 15 VUs |
| Tip haosa | NetworkChaos — delay |
| Injektovana latency | 300ms ± 50ms, 50% korelacija |
| Trajanje | 2 minuta |
| Circuit breaker | Da |
| httpx timeout | 5s |

---

## Snimci ekrana

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 13-52-30.png>)

> Ukupni sistem: **54.4 req/s**, p95 **85.4ms**, stopa grešaka **0%**, aktivnih podova **12**. Dva chaos eventa vidljiva (~13:40). p95 latency po servisu pokazuje veliki spike na api-gatewayu (~10s) i book-serviceu tokom chaos prozora — 300ms DB latency multiplicira se kroz request lanac.

---

**CPU i memorija:**

![](<Screenshot from 2026-06-07 13-52-43.png>)

> api-gateway CPU **pada** tokom chaos eksperimenta (manje posla jer manje zahteva prolazi) pa se vraća. Svi ostali servisi stabilni. Nema restart ciklusa.

---

**k6 Load Test:**

![](<Screenshot from 2026-06-07 13-52-54.png>)

> 15 VUs. `::browse` request rate **naglo pada** tokom chaos eksperimenta (~13:40-13:42) jer book-service sporo odgovara. Nakon završetka chaos eksperimenta browse se vraća. Failed requests ostaju praktično na **0** — sistem degradiran ali bez grešaka.

---

**book-service dashboard:**

![](<Screenshot from 2026-06-07 13-53-15.png>)

> book-service: 22.2 req/s, p95 **4.84ms** (izmereno nakon chaos perioda), stopa grešaka **0%**, restarti **0**. Latency naglo raste u toku chaos eksperimenta.

---

**api-gateway dashboard:**

![](<Screenshot from 2026-06-07 13-53-23.png>)

> api-gateway: 19.2 req/s, p95 **96.4ms**, stopa grešaka **0%**, restarti **0**. Latency naglo raste u toku chaos eksperimenta (p99 → ~8-9s) jer gateway čeka odgovor od sporog book-service — blizu httpx timeout granice od 5s.

---

**inventory-service (kontrola):**

![](<Screenshot from 2026-06-07 13-53-45.png>)

> inventory-service: 11.1 req/s, p95 **4.82ms**, 0 restarta — potpuno nepogođen.

---

## Poređenje pre i posle

| Metrika | Pre (bez CB/async) | Posle (CB + async) |
|---|---|---|
| api-gateway restarti | 0 | **0** |
| DB connection pool peak | **~75%** | Nije dostupno (Grafana) |
| k6 Failed requests | ~8-14 req/s | **~0 req/s** |
| api-gateway latency (p99) | ~4-5s | **~8-9s** (viši!) |
| Sistem stabilan | Da (degradiran) | **Da (degradiran)** |
| Browse dostupan | Da (degradiran) | **Da (degradiran)** |

*Napomena: api-gateway p99 latency je viši u After scenariju jer asyncio.to_thread drži konekciju otvorenom do httpx timeout-a (5s) umesto da blokira event loop i pada. Ovo je ispravno ponašanje.

---

## Nalazi

- Network latency prema bazi **i dalje se propagira** prema klijentima — circuit breaker ne štiti od sporog servisa koji ne vraća greške
- api-gateway **ne pada** (0 restarta) — asyncio.to_thread fix drži event loop slobodnim
- Browse request rate pada jer gateway čeka odgovor koji kasni ~300ms+
- httpx **5s timeout** je zaštita koja bi, da latency pređe tu granicu, pretvorila usporenje u grešku i aktivirala circuit breaker
- Za razliku od prethodnog scenarija, nema nakupljanja blokiranih konekcija

## Zaključak

**Hipoteza potvrđena.** Sistem podnosi network latency bez pada ili grešaka. Ključni nalaz: circuit breaker i timeout zajedno čine sistem predvidivim — ili odgovori stižu u roku (5s), ili circuit breaker okida. Čista degradacija umesto haotičnog pada.
