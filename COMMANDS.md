# Commands

All CLI commands for this repo.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
cp .env.example .env
gcloud auth application-default login
```

## Services

```bash
docker compose up -d db
docker compose down
```

## Chat

```bash
python -m retail_analyst.cli --user alice   # alice, bob or carol
```

In the chat: `/trace` shows the steps of the last answer, `/reports` lists your saved reports, `/export` saves the tables of the last answer as CSV files in `exports/`, `exit` quits. With `TRACE_VERBOSE=1` in `.env`, the trace (`/trace`, `logs/agent.jsonl`) also holds each prompt, the raw model answer and the rows of each query (personal columns are already masked).

## Chat in Docker

No local Python needed; only the env file and Google credentials.

```bash
docker compose build app
docker compose run --rm app --user alice
docker compose run --rm --entrypoint python app -m retail_analyst.observability
```

The container reads the env file at run time (nothing secret is in the image) and mounts,
read-only, the credentials file named by `GOOGLE_APPLICATION_CREDENTIALS` in that env file:
the full path on your computer, e.g. the one `gcloud auth application-default login` prints
(`Credentials saved to file: [...]`). Docker stops with a message if it is empty.
Traces are written to `./logs` and exports to `./exports`.

## Lint and complexity

```bash
ruff check .
ruff format --check .
ruff check --fix . && ruff format .
complexipy -f src
```

## Tests

```bash
pytest tests/unit
pytest tests/integration
pytest tests/acceptance -m acceptance
pytest tests/unit/test_x.py::test_name
```

Acceptance tests call live Gemini and BigQuery: run them only when needed.
