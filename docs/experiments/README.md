🇷🇸 Srpski | [🇬🇧 English](README.en.md)

# Chaos eksperimenti — pregled

Svi eksperimenti prate hipotezom vođenu metodologiju:  
**Definiši steady state → postavi hipotezu → injektuj kvar → posmatraj → zaključi**

---

## API Gateway Fine Tuning

Četiri iteracije load testa koje su iterativno otkrile i otklonile slabosti api-gatewaya. Najvažniji deo projekta — prikazuje kako chaos engineering funkcioniše u praksi.

| Iteracija | Opis | Rezultat |
|---|---|---|
| [Pre circuit breaker-a](API-GW-Before-Circuit-Breaker/experiment.md) | 50 VUs, bez zaštite | 6 pod restarta, kaskadni kvar |
| [Posle circuit breaker-a](API-GW-After-Circuit-Breaker/experiment.md) | pybreaker + 5s timeout | 0 restarta, ali skrivena greška ostala |
| [Otkriće event loop blokade](Load-Test-Without-Async/experiment.md) | sync httpx u async kodu | 9 restarta @ 15 VUs (SIGTERM) |
| [Posle asyncio fixa](Load-Test-With-Async/experiment.md) | asyncio.to_thread + CPU 500m + probe 5s | 0 restarta, 0 neuspešnih zahteva |

Spojena priča kroz sve četiri iteracije: [API-GW-Fine-Tuning/experiment.md](API-GW-Fine-Tuning/experiment.md)

---

## Network Latency — book-service baza podataka

Injekcija 300ms kašnjenja između book-service i PostgreSQL.

| Eksperiment | Link | Ključni nalaz |
|---|---|---|
| Pre fixa | [experiment.md](network-latency-bookdb-Before-Circuit-Breaker/experiment.md) | DB connection pool dostigao 75%, latency propagirao do klijenata |
| Posle fixa | [experiment.md](network-latency-bookdb-After-Circuit-Breaker-And-With-Async/experiment.md) | 0 restarta, 0 grešaka — čista degradacija umesto haotičnog pada |

---

## Pod Failure — order-service

Ubijanje order-service poda i posmatranje oporavka sistema.

| Eksperiment | Link | Ključni nalaz |
|---|---|---|
| Pre fixa | [experiment.md](pod-failure-order-Before-Circuit-Breaker/experiment.md) | 3 restarta, ~14 failed req/s, api-gateway nestabilan |
| Posle fixa | [experiment.md](pod-failure-order-After-Circuit-Breaker-And-With-Async/experiment.md) | 0 restarta na api-gatewayu, ~2 failed req/s, brz oporavak |

---

## HTTP 500 injekcija — order-service (3 iteracije)

Ubacivanje HTTP 500 grešaka na odgovore order-service. Tri iteracije koje su svaka otkrila novi problem.

| Iteracija | Link | Ključni nalaz |
|---|---|---|
| Pre circuit breaker-a | [experiment.md](http-500-order-Before-Circuit-Breaker/experiment.md) | 6 restarta api-gatewaya, thundering herd |
| Posle CB + async (path: *) | [experiment.md](http-500-order-After-Circuit-Breaker-And-With-Async/experiment.md) | 0 restarta api-gatewaya, ali 9 restarta order-service (path: * pogađa /health) |
| Posle probe + path fixa | [experiment.md](http-500-order-After-Probe-And-Path-Fix/experiment.md) | 0 restarta, sistem stabilan, "malo se desilo" = dokaz uspeha |

---

## CPU Stress — inventory-service

80% CPU opterećenje na inventory-service sa 2 worker-a.

| Eksperiment | Link | Ključni nalaz |
|---|---|---|
| CPU stress 80% | [experiment.md](cpu-80-inventory/experiment.md) | Latency propagira, 0 grešaka — circuit breaker ne štiti od sporog servisa |

---

## Rezime svih eksperimenata

| Eksperiment | Target | Pre | Posle |
|---|---|---|---|
| Stress test | api-gateway | 6 restarta, kaskadni kvar | 0 restarta, CB izoluje greške |
| Network latency (300ms DB) | book-service | Pool 75%, degradiran | Stabilan, 0 grešaka |
| Pod failure | order-service | ~14 failed req/s | ~2 failed req/s, brz oporavak |
| HTTP 500 (path: *) | order-service | 6+8 restarta | 0 GW restarta, 9 OS restarta* |
| HTTP 500 (path: /orders*) | order-service | — | 0 restarta, sistem stabilan |
| CPU stress 80% | inventory-service | — | Latency +400ms p99, 0 grešaka |

*path: `*` pogađao `/health` endpoint — popravljeno u trećoj iteraciji
