# Evidenze nella PR

Ogni PR porta la prova che il cambio funziona. Chi la legge non testa a mano.
L'agente sceglie il livello, al massimo tre prove, proporzionali al cambio.

## Come si avvia e si testa

- Avvio in locale: TBD, the CLI does not exist yet (see [COMMANDS.md](../../COMMANDS.md) once it does)
- Unit: `pytest tests/unit`
- Integrazione: `pytest tests/integration`
- Acceptance live: `pytest tests/acceptance -m integration`

## Quanto testare — i livelli

### Livello 0 — una riga, testo, config

Il nome del test rosso→verde e cosa verifica, in una riga.

### Livello 1 — logica o endpoint

Livello 0 + un esempio reale: l'output del comando CLI (domanda, SQL eseguito, risposta)
(es. richiesta/risposta vera, ritorno di un tool, prima/dopo).

## Nella PR

Il formato e la lunghezza della sezione `## Evidence` li decide la skill `pr`.
Per produrre l'evidenza lancia solo i test che servono a produrla, non
l'intera suite.
