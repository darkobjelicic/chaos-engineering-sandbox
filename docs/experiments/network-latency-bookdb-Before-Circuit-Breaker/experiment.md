🇷🇸 Srpski | [🇬🇧 English](experiment.en.md)

# Network Latency — book-service baza podataka (pre circuit breaker-a)

**Datum:** 26.05.2026.  
**Tip:** Chaos eksperiment — NetworkChaos  
**Target:** book-service → PostgreSQL (postgres-book)  
**Alat:** Chaos Mesh + k6  

---

## Hipoteza

Uvođenje 300ms (±50ms) network latencije između book-service i njegove baze podataka propagiraće se prema klijentima kao povećan latency, ali sistem će ostati funkcionalan bez pada servisa.

---

## Podešavanja

| Parametar | Vrednost |
|---|---|
| Virtualni korisnici | 15 VUs |
| Tip haosa | NetworkChaos — delay |
| Injektovana latency | 300ms ± 50ms (jitter), 50% korelacija |
| Trajanje | 2 minuta |
| Circuit breaker | Ne |

**Chaos Mesh konfiguracija:**
```yaml
action: delay
delay:
  latency: 300ms
  jitter: 50ms
  correlation: "50"
direction: to
selector:
  labelSelectors:
    app: book-service
```

---

## Snimci ekrana

**Bookstore Overview — Errors & Health:**

![](<Screenshot from 2026-05-26 20-38-12.png>)

> Nema 5xx ni 4xx grešaka. Active HTTP requests na api-gatewayu osciliraju normalno. Servis je **dostupan ali degradiran**.

---

**CPU i memorija po podu:**

![](<Screenshot from 2026-05-26 20-38-26.png>)

> CPU usage api-gatewaya vidljivo viši (~15-20%) tokom chaos perioda — drži otvorene konekcije duže čekajući na spori book-service.

---

**DB i Disk — Bookstore Overview:**

![](<Screenshot from 2026-05-26 20-38-37.png>)

> Skok DB konekcija za book-service oko 20:30 — konekcije ostaju otvorene duže jer svaki query čeka na odgovor. Disk I/O Read skače na ~80 MB/s kao posledica retry logike i dužeg zadržavanja transakcija.

---

**book-service dashboard:**

![](<Screenshot from 2026-05-26 20-39-49.png>)

> p95 latency na book-service skočio na **436ms**. Request rate **5.24 req/s**, stopa grešaka **0%**.

---

**DB Connection Pool Utilization:**

![](<Screenshot from 2026-05-26 20-40-03.png>)

> DB Connection Pool Utilization dostiže **~75%** u trenutku chaos eksperimenta. Kritičan nivo — pri 100% novi zahtevi počinju da čekaju u redu ili odmah failuju.

---

**k6 Load Test:**

![](<Screenshot from 2026-05-26 20-38-48.png>)

> 15 VUs. `::browse` latency raste tokom trajanja testa (od ~3ms na ~5ms p99). Failed requests osciliraju između **~8 i ~14 req/s**.

---

## Nalazi

- Network latency prema bazi direktno se propagira na krajnje korisnike (povećan latency na browse operacijama)
- Servis **ne pada** — ostaje funkcionalan ali degradiran
- DB connection pool dostigao **75% iskorišćenosti** — u produkciji sa više VUs, pool bi se iscrpio
- Disk I/O skače zbog dužeg trajanja transakcija
- Nema mehanizma koji bi brzo "odseče" sporu bazu i zaštitio ostatak sistema

## Zaključak

**Hipoteza delimično potvrđena.** Sistem ostaje funkcionalan ali latency se propagira prema klijentima. Kritičan nalaz: iskorišćenost DB connection pool-a od 75% pri samo 15 VUs je signal za uzbunu. U produkcijskom scenariju sa više korisnika pool bi se iscrpio i uzrokovao kvar. Preporuka: dodati timeout na DB konekcije i alerting kada connection pool pređe 60%.
