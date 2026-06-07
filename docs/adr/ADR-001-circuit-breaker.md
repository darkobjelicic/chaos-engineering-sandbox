🇷🇸 Srpski | [🇬🇧 English](ADR-001-circuit-breaker.en.md)

# ADR-001: Circuit Breaker u api-gateway

**Status:** Prihvaćeno  
**Datum:** 26.05.2026.  

---

## Kontekst

Stress test sa 50 virtualnih korisnika pokazao je da api-gateway pada **6 puta** za vreme trajanja testa. httpx HTTP klijent nije imao konfigurisan timeout na pozivima prema downstream servisima (book-service, order-service, auth-service, inventory-service). Pod opterećenjem, konekcije prema sporim ili nedostupnim servisima bi se akumulirale, iscrpile resurse i uzrokovale OOM/crash ciklus koji bi se ponavljao dok je load aktivan.

Grafana metrike pokazale su da gateway pada (Exit Code != 0, pod restarti) ali bez vidljivih 5xx grešaka u HTTP metrikama — greška se gubila na nivou konekcije, ne HTTP sloja.

---

## Odluka

Implementirati **circuit breaker pattern** u api-gateway koristeći `pybreaker` biblioteku, sa zasebnim circuit breaker-om po downstream servisu.

Konfiguracija:
- `fail_max = 5` — otvori kolo nakon 5 uzastopnih grešaka
- `reset_timeout = 30s` — half-open stanje nakon 30 sekundi
- `httpx timeout = 5s` — svaki HTTP poziv se odseče nakon 5 sekundi

Kada je kolo otvoreno, gateway odmah vraća `503 Service Unavailable` umesto da čeka i akumulira konekcije.

---

## Razmatrane alternative

**A) Samo HTTP timeoutovi (bez circuit breaker-a)**  
Timeout sprečava beskonačno čekanje, ali bez circuit breaker-a svaki zahtev i dalje pokušava da kontaktira pokvareni servis. Pod visokim loadom, 5s timeout × N VUs = i dalje može da iscrpi resurse.

**B) Retry sa exponential backoff**  
Korisno za kratke tranzijentne greške, ali bez circuit breaker-a stvara "thundering herd" — svi klijenti retryuju istovremeno i dodatno opterećuju već pokvareni servis.

**C) pybreaker (odabrano)**  
Kombinacija timeoutova i circuit breaker-a: timeout ograničava trajanje jednog poziva, circuit breaker ograničava broj pokušaja prema pokvarenom servisu. Kolo se otvori, gateway vraća brze 503, downstream servis dobija prostor da se oporavi.

**D) Hystrix / Resilience4j**  
JVM ekosistem, nije primenljivo za Python.

---

## Posledice

- api-gateway više ne ruši pod pod opterećenjem — 0 novih restarta u verifikacijskom testu
- 5xx greške sada **vidljive** u metrikama (503 od CB) umesto skrivenih iza pada poda — poboljšana observabilnost
- Dodata zavisnost: `pybreaker==1.0.2`
- Napomena: circuit breaker štiti od grešaka, ali ne od sporog downstream servisa. Timeout od 5s je zaštita od sporosti.
