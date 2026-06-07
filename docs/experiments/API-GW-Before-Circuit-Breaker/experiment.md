🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# Stress Test — api-gateway (pre circuit breaker-a)

**Datum:** 25.05.2026.  
**Tip:** Load / Stress test  
**Target:** api-gateway  
**Alat:** k6  

---

## Hipoteza

Sistem će podneti opterećenje od 50 virtualnih korisnika bez pada servisa. api-gateway će prosleđivati zahteve downstream servisima i vraćati odgovore u razumnom latenciju.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 50 VUs |
| Ramp-up | 2 min → 50% → 3 min → 100% |
| Trajanje | ~10 min sustained |
| Endpoint | `http://api.bookstore.local` |
| httpx timeout | ∞ (nije konfigurisan) |
| Circuit breaker | Ne |

---

## Snimci ekrana

**api-gateway dashboard — početak testa:**

![](<Screenshot from 2026-05-25 22-58-33.png>)

> p95 latency skočio na **939ms**, vidljivo **6 pod restarta** odmah. Pod count oscilira između 0 i 1 dok Kubernetes stalno rekreira pod.

---

![](<Screenshot from 2026-05-25 22-59-24.png>)

> Request rate pada na gotovo 0 za vreme restarta poda. Latency naglo raste (p99 > 4s).

---

**Bookstore Overview — sistemski pregled:**

![](<Screenshot from 2026-05-25 23-03-06.png>)

> Ukupni p95 latency sistema **2.01s**. api-gateway dominira latencyjem u odnosu na sve ostale servise.

---

**CPU i memorija po podu:**

![](<Screenshot from 2026-05-25 23-03-33.png>)

> api-gateway CPU usage skače i pada u ritmu restarta. Ostali servisi stabilni i nepogođeni.

---

**k6 Load Test panel:**

![](<Screenshot from 2026-05-25 23-04-47.png>)

> 50 aktivnih VUs. k6 beleži **~14 failed req/s** kontinuirano. Request rate za `::browse` skače i pada u ritmu restart ciklusa. `::order` praktično nije dostupan.

---

**Errors & Health:**

![](<Screenshot from 2026-05-25 23-22-40.png>)

> Panel za 5xx greške prikazuje "No data" — gateway pada (SIGTERM) pre nego što uspe da vrati HTTP error response. Greška se gubi na nivou konekcije.

---

## Nalazi

- api-gateway se srušio **6 puta** za vreme trajanja testa
- Root cause: `httpx` bez timeoutova — veze prema downstream servisima akumuliraju se dok ne iscrpe resurse, što dovodi do OOM/crash ciklusa
- Kubernetes restartuje pod, ali situacija se ponavlja čim novi pod primi saobraćaj
- Klasičan **kaskadni kvar** — jedan spori upstream dovoljan je da sruši gateway
- 5xx greške nisu vidljive u metrikama jer pod pada pre nego što odgovori

## Zaključak

**Hipoteza oborena.** Sistem nije u stanju da podnese 50 VUs bez zaštitnih mehanizama. Identifikovana potreba za circuit breaker-om i HTTP timeoutovima na svim downstream pozivima.
