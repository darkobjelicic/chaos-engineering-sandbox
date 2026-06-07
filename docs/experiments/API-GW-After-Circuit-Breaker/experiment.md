🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# Stress Test — api-gateway (posle circuit breaker-a)

**Datum:** 26.05.2026.  
**Tip:** Load / Stress test  
**Target:** api-gateway  
**Alat:** k6  

---

## Hipoteza

Uvođenje circuit breaker-a (pybreaker, fail_max=5, reset_timeout=30s) i 5s timeoutova na httpx pozivima sprečiće kaskadni kvar. api-gateway neće padati pod opterećenjem od 50 VUs.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 50 VUs |
| Ramp-up | 2 min → 50% → 3 min → 100% |
| Trajanje | ~10 min sustained |
| httpx timeout | 5s |
| Circuit breaker | pybreaker (fail_max=5, reset_timeout=30s) |
| Promena u kodu | `pybreaker==1.0.2` dodat u requirements |

---

## Snimci ekrana

**api-gateway dashboard:**

![](<Screenshot from 2026-05-26 19-47-36.png>)

> **5 pod restarta** vidljivo na početku (stari podovi iz prethodnog stanja). Tokom samog testa nema novih rušenja. p95 latency stabilniji.

---

**Bookstore Overview:**

![](<Screenshot from 2026-05-26 19-47-59.png>)

> Ukupni p95 latency sistema **1.46s** — niži nego u prethodnom scenariju. Svih **12 podova ostaje Running** tokom celog testa.

---

**Errors & Health:**

![](<Screenshot from 2026-05-26 19-48-15.png>)

> **Nema podataka za 5xx i 4xx greške** — circuit breaker preuzima saobraćaj i vraća brze 503 odgovore umesto da čeka i ruši se. Active HTTP requests prikazuje normalan obrazac bez nakupljanja konekcija.

---

**DB i Disk panel:**

![](<Screenshot from 2026-05-26 19-49-03.png>)

> DB konekcije stabilne, Disk I/O Read skače na ~35 MB/s tokom intenzivnog load perioda — normalno ponašanje pod opterećenjem.

---

**k6 Load Test panel:**

![](<Screenshot from 2026-05-26 19-49-16.png>)

> 50 VUs. p99 latency za `::browse` **~15ms**, za `::order` **~15ms** — drastično poboljšanje u odnosu na prethodni test. Failed requests i dalje prisutni (~14-20/s) jer circuit breaker odbija zahteve dok je kolo otvoreno, ali sistem **ne pada**.

---

## Nalazi

| Metrika | Pre circuit breaker-a | Posle circuit breaker-a |
|---|---|---|
| Pod restarti tokom testa | 6 | 0 (novi) |
| 5xx greške | skrivene (pad poda) | 0 |
| Sistem ostaje stabilan | Ne | Da |
| p95 latency (Overview) | ~2.01s | ~1.46s |
| k6 p99 latency | >4s | ~15ms |

- Circuit breaker sprečava nakupljanje blokiranih konekcija
- Gateway više ne ruši pod — umesto pada, vraća 503 dok je kolo otvoreno
- Sistem ostaje **delimično dostupan** čak i pod maksimalnim opterećenjem

## Zaključak

**Hipoteza potvrđena.** Circuit breaker eliminiše kaskadni kvar. Sistem prolazi stress test bez novih pad podova. Međutim, tokom ovog testa otkrivena je nova skrivena slabost: httpx pozivi su bili sinhroni unutar async funkcija, što blokira event loop. Ta slabost nije uzrokovala pad ovde, ali ispoljila se u kasnijim testovima. _(Vidi: Load-Test-Without-Async)_
