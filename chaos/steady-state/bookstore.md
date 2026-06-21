🇷🇸 Srpski | [🇬🇧 English](bookstore.en.md)

# Steady-State Definicija — Bookstore

Steady-state opisuje kako se sistem ponaša u normalnim uslovima — bez aktivnih chaos eksperimenata, pod tipičnim opterećenjem. Svaki chaos eksperiment meri koliko sistem odstupa od ovog stanja i da li se vraća u njega nakon prestanka injekcije greške.

---

## Referentno opterećenje

Steady-state se meri **load testom** (10 VUs, 25 minuta) koji simulira realne korisničke tokove:
- 70% korisnika pretražuje knjige i inventar (`browse` grupa)
- 30% korisnika pravi porudžbine (`order` grupa)

```bash
k6 run load-testing/k6/scripts/load.js
```

---

## HTTP performanse

| Metrika | Granica |
|---|---|
| Error rate (ukupno) | < 5% |
| p95 latency — browse (`/books`, `/inventory`) | < 500ms |
| p95 latency — order (`/orders`) | < 1500ms |
| p95 latency (ukupno) | < 1000ms |

Ove vrednosti odgovaraju k6 thresholds iz `load.js` i predstavljaju prihvatljivo ponašanje sistema pod normalnim opterećenjem.

---

## Zdravlje klastera

Pod normalnim uslovima, svi podovi ostaju u stanju `Running` i `Ready` tokom celog trajanja load testa bez ijednog restarta. CrashLoopBackOff ne bi trebalo da se pojavi ni na jednom podu.

```bash
kubectl get pods -n bookstore
```

---

## Circuit Breaker stanje

Sva četiri circuit breaker-a u api-gateway (book-service, order-service, auth-service, inventory-service) ostaju u stanju `CLOSED` tokom celog load testa. Nema dovoljno grešaka da se dosegne prag od 5 uzastopnih failova koji bi otvarao kolo.

---

## RabbitMQ

Komunikacija između order servisa i notification servisa teče bez zastoja. Queue depth za `orders` ostaje ispod 100 poruka — poruke se konzumiraju brže nego što pristižu.

```bash
kubectl exec -n bookstore deploy/rabbitmq -- rabbitmqctl list_queues name messages
```

---

## Vremenski okvir oporavka

Ako chaos eksperiment izazove odstupanje od gornjeg stanja, sistem se smatra oporavljenim kada se sve metrike vrate unutar definisanih granica **unutar 2 minute** od prestanka injekcije greške.
