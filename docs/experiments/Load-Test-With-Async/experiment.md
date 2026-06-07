🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# Load Test — Verifikacija asyncio.to_thread + resource fixa (sa async fixom)

**Datum:** 07.06.2026.  
**Tip:** Verifikacijski load test — potvrda ispravke  
**Target:** api-gateway  
**Alat:** k6  

---

## Kontekst

Nakon što je otkriven problem sa blokiranim event loop-om i CPU throttlingom (vidi `Load-Test-Without-Async`), primenjena su tri fixa:

| Fix | Promena |
|---|---|
| asyncio.to_thread | httpx pozivi se izvršavaju u thread pool-u — event loop ostaje slobodan |
| CPU limit | 200m → 500m (0.2 → 0.5 core-a) |
| Probe timeout | 1s → 5s (liveness + readiness) |

Ovaj load test služi kao verifikacija da sva tri fixa zajedno rešavaju problem.

---

## Hipoteza

api-gateway sa asyncio.to_thread fixom i povećanim resursima podnosi load od 15 VUs bez ijednog pod restarta i bez neuspešnih zahteva.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 15 VUs |
| Trajanje | 55 min sustained |
| httpx pozivi | `asyncio.to_thread()` — async ✅ |
| CPU limit | 500m |
| Memory limit | 256Mi |
| Probe timeout | 5s |

---

## Snimci ekrana

**k6 Load Test panel:**

![](<Screenshot from 2026-06-07 13-33-20.png>)

> 15 stabilnih VUs. `::browse` request rate **~25-30 req/s**, `::order` **~2-3 req/s**. k6 p99 latency ~1.5ms. **Failed requests = 0** — drastična razlika u odnosu na prethodni test gde je failed bio ~10-15 req/s kontinuirano.

---

**CPU i memorija po podu:**

![](<Screenshot from 2026-06-07 13-33-42.png>)

> api-gateway CPU raste do ~40% i **stabilizuje se** — nema padova na 0 koji su označavali restart cikluse. Memorija stabilna na ~48-64 MiB. Pod više ne restartuje.

---

**Bookstore Overview:**

![](<Screenshot from 2026-06-07 13-34-01.png>)

> Ukupni sistem: **76.9 req/s**, p95 latency **107ms**, stopa grešaka **0%**, aktivnih podova **12** — sve zeleno.

---

**api-gateway Service Detail — ključni snimak:**

![](<Screenshot from 2026-06-07 13-34-38.png>)

> api-gateway: 34.8 req/s, p95 latency **245ms**, stopa 5xx grešaka **0%**, restarti **= 0**. Pod Count ostaje stabilno na 1 tokom celog testa. CPU raste do ~0.4 core-a ali ne prouzrokuje restart — event loop je slobodan zahvaljujući asyncio.to_thread.

---

**order-service (kontrola):**

![](<Screenshot from 2026-06-07 13-35-06.png>)

> order-service: 4.55 req/s, p95 **206ms**, 0 restarta, CPU ~0.08 core-a — stabilan.

---

**book-service (kontrola):**

![](<Screenshot from 2026-06-07 13-35-15.png>)

> book-service: 21.9 req/s, p95 **4.99ms**, 0 restarta, CPU ~0.06 core-a — stabilan i brz.

---

## Poređenje sa prethodnim testom

| Metrika | Bez async fixa | Sa async fixom |
|---|---|---|
| Pod restarti | 9 za ~30 min | **0** |
| k6 Failed requests | ~10-15 req/s | **0 req/s** |
| Stabilnost Pod Count-a | Pada na 0 višestruko | **Stabilan na 1** |
| Stopa grešaka (5xx) | 0% (pod pada pre odgovora) | **0%** |
| CPU obrazac | Skači → pad → skači → pad | **Raste i stabilizuje se** |
| Sistem upotrebljiv | Ne | **Da** |

---

## Nalazi

- **asyncio.to_thread eliminiše blokadu event loop-a** — health endpoint odgovara čak i pod punim CPU opterećenjem
- CPU raste do ~40% i stabilizuje se — threading overhead je realan ali prihvatljiv
- 0 neuspešnih zahteva tokom celog testa — sistem je **potpuno dostupan** pod 15 VUs
- Latency na api-gatewayu (~245ms p95) je veći nego na direktnim servisima jer je gateway dodatni hop + thread pool overhead
- Memorija ostaje stabilna ~48-64 MiB — daleko ispod limita od 256Mi

## Zaključak

**Hipoteza potvrđena.** Sva tri fixa zajedno rešavaju problem. api-gateway je spreman za chaos eksperimente. Ovo zatvara iterativni ciklus: problem otkriven pod opterećenjem → root cause analiziran → fix primenjen → verifikovan.
