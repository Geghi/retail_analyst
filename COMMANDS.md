# Commands

All CLI commands for this repo.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
cp .env.example <your-local-env-file>
gcloud auth application-default login
```

## Services

```bash
docker compose up -d db
docker compose down
```

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
