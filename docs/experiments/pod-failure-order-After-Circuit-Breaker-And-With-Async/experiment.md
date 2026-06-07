🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# Pod Failure — order-service (posle circuit breaker-a + async fixa)

**Datum:** 07.06.2026.  
**Tip:** Chaos eksperiment — PodChaos  
**Target:** order-service  
**Alat:** Chaos Mesh + k6  

---

## Kontekst

Isti eksperiment kao `pod-failure-order-Before-Circuit-Breaker`, pokrenut nakon implementacije circuit breaker-a i asyncio.to_thread fixa. Cilj je da se verifikuje da zaštitni mehanizmi poboljšavaju ponašanje sistema tokom pada poda.

---

## Hipoteza

Circuit breaker na api-gatewayu sprečiće kaskadni kvar tokom pada order-service poda. api-gateway neće padati, a neuspešni zahtevi će biti minimalni i kratkotrajni.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 15 VUs |
| Tip haosa | PodChaos — pod-failure |
| Mode | one (ubija jedan pod) |
| Trajanje | 2 minuta |
| Circuit breaker | Da (fail_max=5, reset_timeout=30s) |
| httpx | asyncio.to_thread |

---

## Snimci ekrana

**Bookstore Overview — sistemski pregled:**

![](<Screenshot from 2026-06-07 14-20-09.png>)

> Ukupni sistem: **80.1 req/s**, p95 latency **82.7ms**, stopa grešaka **0%**, aktivnih podova **12**. Chaos eksperiment jasno vidljiv (~13:55, crvene isprekidane linije) kao kratki latency skok na api-gatewayu, ali sistem ostaje funkcionalan.

---

**Errors & Health:**

![](<Screenshot from 2026-06-07 14-20-24.png>)

> api-gateway 5xx stopa grešaka dostiže **~12.5%** u kratkom prozoru tokom chaos eksperimenta dok se circuit breaker aktivira, potom odmah pada na **0%**. Nema 4xx grešaka. Active HTTP requests ostaju na minimumu (1-3) — nema nakupljanja blokiranih konekcija.

---

**CPU i memorija po podu:**

![](<Screenshot from 2026-06-07 14-20-34.png>)

> api-gateway CPU stabilan na ~40% kroz ceo test. order-service CPU pada na 0 u momentu chaos eksperimenta i vraća se pri restartu. Ostali servisi potpuno nepogođeni.

---

**k6 Load Test panel:**

![](<Screenshot from 2026-06-07 14-20-44.png>)

> 15 VUs. Failed requests dostižu samo **~2 req/s** u kratkom trenutku chaos eksperimenta — pa odmah padaju nazad na 0. p99 latency ostaje ispod **0.7ms** za browse i **0.5ms** za order. Sistem se oporavlja za sekunde.

---

**order-service dashboard:**

![](<Screenshot from 2026-06-07 14-21-01.png>)

> order-service: **3 pod restarta**, p95 latency **93.3ms**, stopa grešaka **0%**. Pod Count pada i vraća se, ali sistem nastavlja da opslužuje zahteve čim pod postane dostupan.

---

**api-gateway dashboard:**

![](<Screenshot from 2026-06-07 14-21-09.png>)

> api-gateway: 19.3 req/s, p95 **98.8ms**, stopa 5xx grešaka **0%**, restarti **= 0**. Ključna razlika u odnosu na prethodni eksperiment gde je api-gateway imao 5 restarta — ovde ni jedan.

---

**notification-service (provera izolacije):**

![](<Screenshot from 2026-06-07 14-21-19.png>)

> notification-service: **0 restarta**, p95 **4.75ms** — potpuno stabilan, kvar se nije proširio.

---

## Poređenje pre i posle

| Metrika | Pre (bez CB) | Posle (CB + async) |
|---|---|---|
| api-gateway restarti | 5 | **0** |
| k6 Failed requests (peak) | ~14 req/s | **~2 req/s** |
| Trajanje neuspešnih zahteva | Kontinuirano | **Kratki spike** |
| 5xx stopa grešaka (peak) | Skrivene (pad poda) | **~12.5% → brzo 0%** |
| Oporavak sistema | Spor, nestabilan | **Brz, automatski** |
| api-gateway stabilan | Ne | **Da** |

---

## Nalazi

- Circuit breaker apsorbuje pad order-service poda — api-gateway više ne pada
- Failed requests su **7x manji** i kratkotrajni (~2 req/s u sekundama vs ~14 req/s kontinuirano)
- 5xx greške su sada vidljive u metrikama (kratki skok na ~12.5%) jer gateway vraća 503 umesto da se ruši — ovo je **poboljšanje observabilnosti**
- Kubernetes samoizlečenje i dalje funkcioniše — order-service se oporavlja bez intervencije
- Izolacija kvara potvrđena — notification-service, book-service i ostali potpuno nepogođeni

## Zaključak

**Hipoteza potvrđena.** Circuit breaker sprečava kaskadni kvar tokom pod failure-a. api-gateway ostaje stabilan (0 restarta), neuspešni zahtevi su minimalni i kratkotrajni, a sistem se oporavlja automatski i brzo.
