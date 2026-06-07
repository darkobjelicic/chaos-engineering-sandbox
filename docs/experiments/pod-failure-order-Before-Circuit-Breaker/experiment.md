🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# Pod Failure — order-service (pre circuit breaker-a)

**Datum:** 26.05.2026.  
**Tip:** Chaos eksperiment — PodChaos  
**Target:** order-service  
**Alat:** Chaos Mesh + k6  

---

## Hipoteza

Kubernetes će detektovati pad order-service poda i restartovati ga u razumnom roku. Sistem će biti privremeno degradiran tokom restart ciklusa ali će se oporaviti. Ostali servisi neće biti pogođeni.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 15 VUs |
| Tip haosa | PodChaos — pod-failure |
| Mode | one (ubija jedan pod) |
| Trajanje | 2 minuta (ponovljeno) |
| Circuit breaker | Ne |

**Chaos Mesh konfiguracija:**
```yaml
action: pod-failure
mode: one
selector:
  labelSelectors:
    app: order-service
duration: 2m
```

---

## Snimci ekrana

**order-service dashboard:**

![](<Screenshot from 2026-05-26 20-51-49.png>)

> **3 pod restarta** vidljiva. p95 latency na order-service dostiže **~1.67s**. Crvene isprekidane linije označavaju trenutke chaos eksperimenta.

---

**Bookstore Overview:**

![](<Screenshot from 2026-05-26 20-52-06.png>)

> Ukupni sistem: p95 latency **2.15s**, request rate ~15 req/s. Latency raste kod svih servisa koji zavise od order-service u trenutku pada.

---

**CPU i memorija po podu:**

![](<Screenshot from 2026-05-26 20-52-23.png>)

> Dve crvene isprekidane linije (dva chaos eventa) jasno vidljive. order-service CPU i memorija padaju na 0 tokom kvara, skaču nazad pri restartu.

---

**DB i Disk:**

![](<Screenshot from 2026-05-26 20-52-32.png>)

> DB konekcije za order-service padaju na 0 tokom chaos eksperimenta i oporavljaju se nakon restarta. Disk I/O skače pri restartu (inicijalizacija konekcija).

---

**k6 Load Test panel:**

![](<Screenshot from 2026-05-26 20-52-42.png>)

> 15 VUs. U trenutku chaos eksperimenta (~20:43 i ~20:45), `::order` latency skače na **~7ms p99**, failed requests dostižu peak od **~14 req/s**. Sistem se oporavio između dva eventa.

---

**api-gateway dashboard (kontrola):**

![](<Screenshot from 2026-05-26 20-53-19.png>)

> api-gateway: **5 restarta** (iz ranijeg testa), ali nema novih rušenja tokom ovog eksperimenta. p95 ~2.39s — oseća sporu konekciju prema palom order-service.

---

**notification-service (provera izolacije):**

![](<Screenshot from 2026-05-26 20-53-52.png>)

> notification-service: **0 restarta**, p95 latency **7.33ms** — potpuno stabilan. Potvrđuje da je kvar bio izolovan na order-service.

---

## Nalazi

- Pod failure uzrokovao **kratke intervale nedostupnosti** (trajanje restart ciklusa ~30-60s)
- Kubernetes je uspešno restartovao pod u razumnom roku
- **Izolacija kvara funkcionisala** — notification-service, book-service, auth-service nisu bili pogođeni
- Tokom restarta, zahtevi prema order-service odmah failuju bez retry mehanizma
- api-gateway oseća kvar (povećan latency) ali ne pada sam

## Zaključak

**Hipoteza potvrđena.** Kubernetes samoizlečenje funkcioniše. Kvar je izolovan bez propagacije na ostale servise. Slabost: nema retry logike na strani api-gatewaya — zahtevi koji stignu za vreme restarta odmah failuju umesto da sačekaju ili pokušaju ponovo.
