# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --upgrade pip \
    && python -m pip install .

COPY alembic.ini ./
COPY alembic ./alembic
COPY config/competitions.example.yaml \
     config/competitions_history.yaml \
     config/discord_channels.example.yaml \
     config/discord_webhooks.example.yaml \
     ./config/
COPY docs/api_football_reference.md \
     docs/api_football_reference.json \
     docs/api_football_players_reference.md \
     docs/api_football_players_reference.json \
     docs/api_football_players_cache.json \
     ./docs/
COPY scripts/docker-entrypoint.sh \
     scripts/init_local.sh \
     scripts/run_predict_today.sh \
     ./scripts/

RUN chmod +x /app/scripts/docker-entrypoint.sh \
    && mkdir -p /app/data/raw /app/data/processed /app/data/models \
    && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["doctor"]
