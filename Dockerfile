FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt pyproject.toml ./
COPY src ./src
RUN pip install -r requirements.txt

COPY config ./config
COPY golden ./golden

RUN useradd --uid 1000 --create-home analyst && mkdir -p /app/logs && chown analyst /app/logs
USER analyst

ENTRYPOINT ["python", "-m", "retail_analyst.cli"]
