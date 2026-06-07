# FootLumen API V1 Contract

FootLumen API V1 is a read-only HTTP surface for data already produced by the existing CLI, crons, models and Discord workflows. It must not trigger predictions, API-Football refreshes, Discord publication, settlement, ticket mutation or any other write path.

## Initial Endpoints

All routes are under `/api/v1` and require API access while the API is in shadow mode.

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | API, DB and runtime health without secrets. |
| `GET` | `/version` | Package/API version metadata. |

Planned read-only routes for later sprints include fixtures, predictions, O/U decisions, World Cup combo tickets, recent results and performance summaries.

## Public DTO Rules

Responses must use explicit Pydantic DTOs. They must never return SQLAlchemy models, raw snapshots, `payload_json`, Discord webhook data, secrets, DB URLs or unfiltered staff-only warnings.

## Local Run

```bash
FOOTLUMEN_API_ENABLED=true FOOTLUMEN_API_TOKEN=dev-token \
uvicorn football_predictor.web_api.app:app --reload --port 8000

curl -H "Authorization: Bearer dev-token" \
  http://127.0.0.1:8000/api/v1/health
```
