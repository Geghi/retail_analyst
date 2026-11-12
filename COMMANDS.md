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

In the chat: `/trace` shows the steps of the last answer, `/reports` lists your saved reports, `exit` quits.

## Chat in Docker

No local Python needed; only the env file and Google credentials.

```bash
docker compose build app
docker compose run --rm app --user alice
docker compose run --rm --entrypoint python app -m retail_analyst.observability
```

The container reads the env file at run time (nothing secret is in the image) and mounts
`GOOGLE_APPLICATION_CREDENTIALS` (default: your `gcloud` application-default credentials)
read-only. Traces are written to `./logs`.

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
pytest tests/acceptance -m integration
pytest tests/unit/test_x.py::test_name
```

Acceptance tests call live Gemini and BigQuery: run them only when needed.
