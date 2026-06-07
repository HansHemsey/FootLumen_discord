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
| `GET` | `/predictions/latest` | Latest public-safe 1X2 prediction DTOs by fixture. |
| `GET` | `/predictions/{fixture_id}` | Latest 1X2 prediction for one fixture. |
| `GET` | `/ou/latest` | Latest public-safe O/U prediction DTOs by fixture. |
| `GET` | `/ou/{fixture_id}` | Latest O/U prediction for one fixture. |
| `GET` | `/combos/today` | Combo tickets for one local day. |
| `GET` | `/combos/latest` | Latest combo tickets. |
| `GET` | `/combos/{ticket_key}` | One combo ticket with filtered legs and settlement summary. |
| `GET` | `/results/recent` | Recent finished fixtures with compact prediction/result context. |
| `GET` | `/performance/summary` | Aggregate counters without ROI assumptions. |

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

## Prediction Endpoints

### `GET /api/v1/predictions/latest`

Query parameters:

- `competition_key`: optional competition filter.
- `date`: optional fixture local date as `YYYY-MM-DD`.
- `limit`: optional, default `20`, max `100`.
- `only_public`: optional boolean, default `false`.
- `include_no_bet`: optional boolean, default `true`.

The service prefers V3 1X2 predictions when present for a fixture and falls back to legacy `ModelPrediction` only when no V3 row exists. Responses are wrapped as `{ "items": [...], "meta": { ... } }`.

### `GET /api/v1/predictions/{fixture_id}`

Returns the latest 1X2 prediction for the fixture, or `404 prediction_not_found`.

The DTO includes fixture information, probabilities, model version, confidence, data-quality score, publication decision when present, public explanations and filtered public warnings. It intentionally hides feature snapshot IDs, raw model internals and raw `payload_json`.

Example:

```bash
curl -H "Authorization: Bearer dev-token" \
  "http://127.0.0.1:8000/api/v1/predictions/latest?competition_key=fifa_world_cup_2026&limit=20"
```

## O/U Endpoints

### `GET /api/v1/ou/latest`

Query parameters:

- `competition_key`: optional competition filter.
- `date`: optional fixture local date as `YYYY-MM-DD`.
- `limit`: optional, default `20`, max `100`.
- `only_value_picks`: optional boolean, default `false`.
- `include_no_bet`: optional boolean, default `true`.

### `GET /api/v1/ou/{fixture_id}`

Returns the latest O/U prediction for the fixture, or `404 ou_prediction_not_found`.

The DTO exposes O/U V2 forecast/value fields, confidence V2, edge/EV, publication decision and no-bet reason when present. Legacy O/U rows may return nullable V2 fields, but raw expert probability payloads and raw snapshots are never returned.

Example:

```bash
curl -H "Authorization: Bearer dev-token" \
  "http://127.0.0.1:8000/api/v1/ou/latest?only_value_picks=true&limit=20"
```


## Combo Endpoints

### `GET /api/v1/combos/today`

Query parameters:

- `date`: optional `YYYY-MM-DD`; defaults to the local date in `APP_TIMEZONE`.
- `competition_key`: optional, defaults to `fifa_world_cup_2026`.
- `include_staff`: optional boolean, default `false`.
- `limit`: optional, default `10`, max `50`.

When `include_staff=false`, strictly staff-only/watchlist/no-bet tickets are hidden. V1 shadow consumers can request `include_staff=true` for premium/internal dashboards, but payloads and staff-only warning internals remain filtered.

### `GET /api/v1/combos/latest`

Query parameters:

- `competition_key`: optional competition filter.
- `include_staff`: optional boolean, default `false`.
- `limit`: optional, default `10`, max `50`.

### `GET /api/v1/combos/{ticket_key}`

Returns one `ComboTicketDTO`, including filtered legs and a nullable `settlement` summary when settlement data already exists. The endpoint never runs settlement and never mutates ticket status. Missing tickets return `404 combo_not_found`.

Example:

```bash
curl -H "Authorization: Bearer dev-token" \
  "http://127.0.0.1:8000/api/v1/combos/today?include_staff=false"
```

## Result Endpoints

### `GET /api/v1/results/recent`

Query parameters:

- `competition_key`: optional competition filter.
- `days`: optional, default `7`, max `30`.
- `limit`: optional, default `50`, max `100`.

Returns finished fixtures only, with score, computed 1X2 result, nullable O/U result, compact latest prediction summaries and a simple combo impact count. Missing prediction or combo data is returned as `null`/`0`; no recalculation is performed.

## Performance Endpoint

### `GET /api/v1/performance/summary`

Query parameters:

- `competition_key`: optional competition filter.
- `days`: optional, default `30`, max `365`.

Returns counters for predictions, O/U rows, combo tickets, no-bet rows, public Discord publication estimate, and settled/correct legacy 1X2 predictions when the finished fixture data is available. ROI is intentionally returned as `null` with a note until stakes, executable odds and settlements are complete enough to be reliable.

## DTO Families

- `FixtureSummaryDTO`: fixture identity, teams, kickoff times in UTC/Paris, status, venue and public data-quality flags.
- `Prediction1X2DTO`: public 1X2 probabilities, prediction time, model version, confidence, public explanations and filtered warnings.
- `OUPredictionDTO`: O/U V2 forecast/value fields, edge/EV, confidence V2, publication decision and no-bet reason.
- `ComboTicketDTO` / `ComboLegDTO`: public combo ticket metrics, filtered settlement summary, public warnings and readable leg selections.
- `RecentResultDTO`: finished fixture result with compact prediction and combo impact context.
- `PerformanceSummaryDTO`: aggregate public counters only, without raw Discord or model payloads and without invented ROI.

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
