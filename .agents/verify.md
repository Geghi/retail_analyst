# Verify recipe — opsfleet-task-assignment

## Run

- Start: `docker compose up -d db`, then the app CLI (TBD: the CLI does not exist yet, see `COMMANDS.md` once it does)
- Env and seed data: copy `.env.example` to a local env file and fill `GEMINI_API_KEY` and `GCP_PROJECT_ID`; BigQuery auth via `gcloud auth application-default login`.
- Test credentials: simulated users, no real accounts (TBD: where they are defined).
- Stop: exit the CLI, `docker compose down`

## Drive

Feed questions to the app CLI and read stdout (TBD: exact invocation once the CLI exists).

## Angles

1. The changed flow, happy path, end to end.
2. Edge inputs: empty message, very long message, non-analysis request, PII request, another user's product.
3. Adjacent flows that share the changed code (guardrails, report store).
4. Service failure: BigQuery or Gemini unreachable shows a friendly error, the loop keeps running.

## Evidence

The CLI transcript: question, executed SQL, final answer.

## Never

Run unbounded BigQuery queries: `BQ_MAX_BYTES_BILLED` stays set.
