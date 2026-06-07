🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# HTTP 500 injekcija — order-service (pre circuit breaker-a)

**Datum:** 26.05.2026.  
**Tip:** Chaos eksperiment — HTTPChaos  
**Target:** order-service  
**Alat:** Chaos Mesh + k6  

---

## Hipoteza

Ubacivanje HTTP 500 grešaka na odgovore order-service neće uzrokovati pad api-gatewaya — gateway će proslediti greške klijentima bez sopstvenog rušenja.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 15 VUs |
| Tip haosa | HTTPChaos — replace response code |
| Injektovana greška | HTTP 500 na sve odgovore |
| Target port | 8000 |
| Trajanje | 2 minuta |
| Circuit breaker | Ne |

**Chaos Mesh konfiguracija:**
```yaml
action: replace
target: Response
port: 8000
path: "*"
replace:
  code: 500
duration: 2m
```

---

## Snimci ekrana

**api-gateway dashboard:**

![](<Screenshot from 2026-05-26 21-03-49.png>)

> api-gateway: **6 pod restarta**, p95 latency **3.90s**. Gateway prima kontinuirane greške od order-service i ne može da ih izoluje — akumulira blokirane konekcije dok ne padne.

---

**order-service dashboard:**

![](<Screenshot from 2026-05-26 21-04-02.png>)

> order-service: **8 pod restarta**, p95 latency **982ms** pa pada na **0 req/s** — servis prestao da prima saobraćaj jer ga Kubernetes stalno restartuje zbog liveness probe grešaka.

---

**DB konekcije — order-service:**

![](<Screenshot from 2026-05-26 21-04-16.png>)

> DB konekcije na order-service padaju sa 5 na 1 tokom chaos eksperimenta — servis gubi sposobnost normalnog rada sa bazom.

---

**Bookstore Overview:**

![](<Screenshot from 2026-05-26 21-04-37.png>)

> Ukupni sistem: p95 latency **2.54s**, aktivnih podova palo na **11** (order-service je down). api-gateway latency dominira grafom.

---

**Errors & Health — Bookstore Overview:**

![](<Screenshot from 2026-05-26 21-04-51.png>)

> **4xx stopa grešaka na order-service dostiže ~55%** za vreme trajanja chaos eksperimenta. 5xx vidljive na api-gatewayu. Chaos eventi označeni crvenim isprekidanim linijama.

---

**CPU i memorija:**

![](<Screenshot from 2026-05-26 21-05-02.png>)

> api-gateway CPU i memorija osciliraju u ritmu restart ciklusa. Ostali servisi stabilni.

---

**k6 Load Test:**

![](<Screenshot from 2026-05-26 21-05-13.png>)

> 15 VUs. `::order` zahtevi padaju na **0** tokom chaos eksperimenta — klijenti ne mogu da dođu do order-service. `::browse` operacije i dalje rade — parcijalna dostupnost sistema.

---

**notification-service (provera izolacije):**

![](<Screenshot from 2026-05-26 21-07-26.png>)

> notification-service: **0 restarta**, p95 latency **~9ms** — stabilan. Greške se nisu proširile dalje u sistemu.

---

## Nalazi

- HTTP 500 greške od order-service **propagirale su se nagore** i uzrokovale nestabilnost api-gatewaya (6 restarta)
- Kritična razlika od pod-failure eksperimenta: servis je fizički dostupan ali vraća greške — api-gateway bez circuit breaker-a ne zna da razlikuje privremenu grešku od trajnog kvara
- Gateway drži otvorene konekcije, akumulira greške, pada — klasičan **thundering herd** problem
- 4xx stopa grešaka na order-service ~55% — Chaos Mesh je uspešno injektovao greške na više od polovine odgovora
- `::browse` operacije su preživele — sistem je bio **parcijalno dostupan**

## Zaključak

**Hipoteza oborena.** api-gateway bez circuit breaker-a nije u stanju da izoluje greške downstream servisa. Umesto brzog vraćanja greške klijentu, gateway drži otvorene konekcije dok ne padne. Ovo je direktna motivacija za uvođenje circuit breaker-a — što je demonstrirano u eksperimentu `API-GW-After-Circuit-Breaker`.
