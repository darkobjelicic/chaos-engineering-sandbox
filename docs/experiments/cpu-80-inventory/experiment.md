🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# CPU Stress — inventory-service (80% opterećenje)

**Datum:** 07.06.2026.  
**Tip:** Chaos eksperiment — StressChaos  
**Target:** inventory-service  
**Alat:** Chaos Mesh + k6  

---

## Hipoteza

Veštačko CPU opterećenje na inventory servisu prouzrokovaće povećan latency na tom servisu koji će se propagirati prema api-gatewayu, ali sistem će ostati funkcionalan bez grešaka ili pada podova.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 15 VUs |
| Tip haosa | StressChaos — CPU |
| CPU opterećenje | 80% (2 worker-a) |
| Trajanje | 2 minuta |
| Circuit breaker | Da |
| Probe timeout | 5s |

**Napomena:** Grafana pod se restartovao tokom eksperimenta zbog memorijskog pritiska nakon 16 sati rada klastera — vidljiva je samo početna anotacijska linija (~15:13), ne i završna.

---

## Snimci ekrana

**inventory-service dashboard:**

![](<Screenshot from 2026-06-07 15-20-25.png>)

> inventory-service: 9.92 req/s, p95 **6.60ms**, stopa grešaka **0%**, restarti **0**. Latency naglo raste u toku chaos eksperimenta — p99 dostiže **~400ms**. CPU usage skače na ~0.2 core-a dostižući limit. Memorija ostaje stabilna na ~72-76 MiB.

---

**api-gateway dashboard:**

![](<Screenshot from 2026-06-07 15-20-31.png>)

> api-gateway: 16.1 req/s, p95 **679ms**, stopa grešaka **0%**, restarti **0**. Latency se propagirala nagore — gateway čeka odgovor od sporog inventory-servicea ali ne pada. Circuit breaker se nije aktivirao jer nema grešaka, samo usporenje.

---

**book-service (kontrola):**

![](<Screenshot from 2026-06-07 15-20-46.png>)

> book-service: 18.8 req/s, p95 **9.13ms**, 0 restarta — minimalno pogođen. CPU stress je izolovan na inventory-service i nije se proširio.

---

**order-service (kontrola):**

![](<Screenshot from 2026-06-07 15-21-09.png>)

> order-service: 4.30 req/s, p95 **210ms**, 0 restarta — blago povećan latency ali bez grešaka.

---

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 15-21-18.png>)

> Ukupno za sistem: **54.3 req/s**, p95 **133ms**, stopa grešaka **0%**, aktivnih podova **12**. Vidljiva samo jedna anotacijska linija (početak chaos eksperimenta) jer je Grafana pala tokom snimanja.

---

**CPU i memorija po podu:**

![](<Screenshot from 2026-06-07 15-21-31.png>)

> CPU usage na inventory servisu (crvena linija) skače na **~25%** u trenutku chaos eventa. Svi ostali servisi stabilni — kvar je ostao izolovan na jednom podu.

---

**k6 Load Test:**

![](<Screenshot from 2026-06-07 15-21-41.png>)

> 15 VUs (vidljiv ramp-down jer se load test završavao). Neuspešni zahtevi: **~1 req/s** kratko pa odmah pada na 0. Browse ~20-25 req/s stabilan, order ~2 req/s. p99 latency ostaje ispod **1.8ms** — k6 praktično i ne primećuje haos.

---

## Nalazi

- CPU stress na inventory servisu prouzrokuje **latency spike do ~400ms p99** na tom servisu
- Latency se propagira prema api-gatewayu (**679ms p95**) jer gateway čeka odgovor od usporenog servisa
- Circuit breaker **se nije aktivirao** — nema grešaka, samo usporenje. Ovo je bitna razlika od HTTP 500 scenarija: circuit breaker štiti od grešaka, ali ne od sporog servisa
- **0 restarta podova**, **0 neuspešnih zahteva** (praktično) — sistem ostaje potpuno funkcionalan
- Izolacija potvrđena — book-service (~9ms) i ostali servisi nisu pogođeni
- Grafana pod se restartovao tokom eksperimenta zbog memorijskog pritiska — sama observability infrastruktura je potencijalna slabost pri dugotrajnom radu

## Zaključak

**Hipoteza potvrđena.** CPU stress prouzrokuje degradaciju performansi kroz povećan latency, ali ne i kvar sistema. Ključni nalaz: **circuit breaker ne štiti od sporog servisa, već samo od servisa koji vraća greške**. Zaštita od sporog downstream servisa je httpx timeout od 5s koji bi, kada bi latency prešao tu granicu, pretvorio usporenje u grešku i aktivirao circuit breaker.
