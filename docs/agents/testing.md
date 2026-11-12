# Testing — opsfleet-task-assignment

## Layers

| Layer       | Command               | Needs                  |
| ----------- | --------------------- | ---------------------- |
| Unit        | `pytest tests/unit`        | nothing                |
| Integration | `pytest tests/integration` | `docker compose up -d db`; BigQuery and Gemini calls are faked |
| Acceptance  | `pytest tests/acceptance -m integration` | live Gemini key and BigQuery credentials; never run automatically |

Acceptance covers the assignment scenarios end to end: revenue question, PII refusal, unauthorized product, delete with confirmation, BigQuery error recovery.

## Folder structure

```
tests/
  unit/         pure logic: SQL validator, PII masking, authorization scoping
  integration/  Postgres-backed stores (reports, prefs, confirmations, audit)
  acceptance/   live end-to-end scenarios
```

## Isolation

Every integration test creates its own user ids and reports; no test reads another test's rows.
