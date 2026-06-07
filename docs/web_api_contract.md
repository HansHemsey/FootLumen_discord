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

## DTO Families

- `FixtureSummaryDTO`: fixture identity, teams, kickoff times in UTC/Paris, status, venue and public data-quality flags.
- `Prediction1X2DTO`: public 1X2 probabilities, prediction time, model version, confidence, public explanations and filtered warnings.
- `OUPredictionDTO`: O/U V2 forecast/value fields, edge/EV, confidence V2, publication decision and no-bet reason.
- `ComboTicketDTO` / `ComboLegDTO`: public combo ticket metrics, public warnings and readable leg selections.
- `PerformanceSummaryDTO`: aggregate public metrics only, without raw Discord or model payloads.

## Explicitly Forbidden Fields

API responses must not expose:

- `payload_json`, `route_json`, `response_json` or raw API snapshots;
- Discord webhooks, channel routing internals or message payloads;
- API keys, bearer tokens, DB URLs or any secret-looking value;
- feature snapshot IDs and raw model internals;
- staff-only warnings, tracebacks or raw debugging notes.

## Warning Filtering

Internal warning codes are either translated to short public messages or omitted. Examples:

| Internal code | Public message |
| --- | --- |
| `odds_missing` | `Cotes indisponibles` |
| `lineup_missing_close_to_kickoff` | `Composition non confirmee` |
| `data_quality_below_threshold` | `Qualite des donnees insuffisante` |

Unknown warning codes are treated as staff-only and are not returned publicly.

## Local Run

```bash
FOOTLUMEN_API_ENABLED=true FOOTLUMEN_API_TOKEN=dev-token \
uvicorn football_predictor.web_api.app:app --reload --port 8000

curl -H "Authorization: Bearer dev-token" \
  http://127.0.0.1:8000/api/v1/health
```
