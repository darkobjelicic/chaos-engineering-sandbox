🇷🇸 Srpski | [🇬🇧 English](ADR-003-probe-timeout.en.md)

# ADR-003: Liveness/Readiness Probe Timeout — 5s za sve Python servise

**Status:** Prihvaćeno  
**Datum:** 07.06.2026.

---

## Kontekst

Tokom load testa koji je pratio implementaciju circuit breaker-a (ADR-001), api-gateway je nastavio da se restartuje čak i nakon što je event loop blokada rešena (ADR-002). Analiza je pokazala da `/health` endpoint ponekad ne odgovori za manje od 1 sekunde kada je pod pod CPU pritiskom.

Kubernetes je bio konfigurisan sa `timeoutSeconds: 1` za liveness i readiness probe na svim servisima. Pod opterećenjem, Python/FastAPI servis koji radi na 200m CPU može da kasni sa odgovorom na HTTP zahtev — uključujući i health check. Tri uzastopna timeout-a (3 × 1s = 3s) vode do SIGTERM-a i graceful shutdown-a sa Exit Code 0, što izgleda kao nameran restart, a ne crash.

Isti scenario može pogoditi bilo koji Python servis u klasteru pod dovoljnim CPU pritiskom, ne samo api-gateway.

---

## Odluka

Povećati `timeoutSeconds` za liveness i readiness probe sa `1s` na `5s` na svim Python servisima:

- `api-gateway`
- `book-service`
- `order-service`
- `auth-service`
- `inventory-service`
- `notification-service`

Promena je primenjena u odgovarajućim Kubernetes Deployment manifestima.

---

## Razmatrane alternative

**A) Per-servis podešavanje (odabrano kao polazna tačka, zatim prošireno)**  
Inicijalno je razmatrano podešavanje samo za api-gateway gde je problem i uočen. Međutim, jer svi servisi dele isti runtime (Python/FastAPI) i iste CPU limite, odlučeno je da se izmena primeni uniformno — pre nego što isti problem pokrene incident na drugom servisu.

**B) Povećanje CPU limita umesto timeout-a**  
Povećanje CPU limita smanjuje verovatnoću da servis kasni, ali ne eliminiše je. Pod dovoljnim opterećenjem, čak i servis sa 500m CPU može da kasni sa health check odgovorom. Timeout od 5s je sigurnosni sloj nezavisan od CPU konfiguracije.

**C) Zadržavanje 1s timeout-a**  
Previše agresivno za Python servise pod realnim opterećenjem. Kubernetes ne razlikuje "servis je spor" od "servis je pao" — oba scenarija vode do restarta, što maskira stvarni uzrok.

---

## Posledice

- Svi Python servisi tolerišu kratkotrajna kašnjenja u health check odgovoru bez nepotrebnih restarta
- Kubernetes je i dalje efikasan u detekciji stvarno pokvarenih podova — 5s timeout × 3 failova = 15s do SIGTERM-a, što je prihvatljivo
- Izmena primenjena uniformno eliminiše rizik da isti problem ostane nedetektovan na drugim servisima
- Probe timeout od 5s je konzervativna vrednost; može se smanjiti ako CPU limiti budu povećani u budućnosti
