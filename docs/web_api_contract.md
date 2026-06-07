# FootLumen API V1 Contract

FootLumen API V1 is a read-only HTTP surface for data already produced by the existing CLI, crons, models and Discord workflows. It must not trigger predictions, API-Football refreshes, Discord publication, settlement, ticket mutation or any other write path.

## Initial Endpoints

All routes are under `/api/v1` and require API access while the API is in shadow mode.

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | API, DB and runtime health without secrets. |
| `GET` | `/version` | Package/API version metadata. |
| `GET` | `/competitions` | List public competitions known by the local DB. |
| `GET` | `/competitions/{competition_key}` | Return one public competition summary. |
| `GET` | `/fixtures/today` | Fixtures for one local calendar day. |
| `GET` | `/fixtures/upcoming` | Upcoming fixtures over a bounded date window. |
| `GET` | `/fixtures/{fixture_id}` | One fixture summary. |

Planned read-only routes for later sprints include predictions, O/U decisions, World Cup combo tickets, recent results and performance summaries.

## Public DTO Rules

Responses must use explicit Pydantic DTOs. They must never return SQLAlchemy models, raw snapshots, `payload_json`, Discord webhook data, secrets, DB URLs or unfiltered staff-only warnings.

## Competition And Fixture Endpoints

### `GET /api/v1/competitions`

Returns `CompetitionSummary` items with `competition_key`, league/season, name, country, type, category, logo and enabled flag when known.

### `GET /api/v1/competitions/{competition_key}`

Returns `404 competition_not_found` if the key is not present in local DB/config-derived metadata.

### `GET /api/v1/fixtures/today`

Query parameters:

- `date`: optional `YYYY-MM-DD`; defaults to the local date in `APP_TIMEZONE`.
- `competition_key`: optional competition filter.

### `GET /api/v1/fixtures/upcoming`

Query parameters:

- `days`: optional, default `7`, max `30`.
- `competition_key`: optional competition filter.
- `status`: optional fixture `status_short` filter such as `NS`.
- `limit`: optional, default/max `100`.

### `GET /api/v1/fixtures/{fixture_id}`

Returns `404 fixture_not_found` if the fixture does not exist.

Fixture responses include public flags such as `has_1x2_prediction`, `has_ou_prediction`, `has_combo`, `latest_prediction_time` and `data_quality_score`. They never expose fixture `payload_json` or raw snapshots.

Example:

```bash
curl -H "Authorization: Bearer dev-token" \
  "http://127.0.0.1:8000/api/v1/fixtures/today?competition_key=fifa_world_cup_2026"
```

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
