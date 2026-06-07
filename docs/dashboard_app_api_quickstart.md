# FootLumen_app API Quickstart

This guide is for the future `FootLumen_app` dashboard. The dashboard must consume the FootLumen API V1 as a read-only backend. It must not recalculate predictions, call API-Football, publish Discord or mutate tickets.

## Base URLs

Local development:

```env
FOOTLUMEN_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Production shadow target:

```env
FOOTLUMEN_API_BASE_URL=https://api.footlumen.com/api/v1
```

## Authentication

Use one of these headers:

```http
Authorization: Bearer <token>
X-FootLumen-Api-Key: <token>
```

For a frontend app, keep the token server-side only. Do not expose it in public browser env vars such as `NEXT_PUBLIC_*`.

## First Endpoints To Integrate

Start with health and fixture display:

```text
GET /health
GET /version
GET /competitions
GET /fixtures/today?competition_key=fifa_world_cup_2026
GET /fixtures/upcoming?competition_key=fifa_world_cup_2026&days=7
```

Then add prediction surfaces:

```text
GET /predictions/latest?competition_key=fifa_world_cup_2026&limit=20
GET /predictions/{fixture_id}
GET /ou/latest?competition_key=fifa_world_cup_2026&limit=20
GET /ou/{fixture_id}
```

Then add CDM and results widgets:

```text
GET /combos/today?competition_key=fifa_world_cup_2026&include_staff=false
GET /combos/latest?competition_key=fifa_world_cup_2026&limit=10
GET /combos/{ticket_key}
GET /results/recent?competition_key=fifa_world_cup_2026&days=7
GET /performance/summary?competition_key=fifa_world_cup_2026&days=30
```

## Main Types

Use these DTO families as frontend models:

- `CompetitionSummary`
- `FixtureSummaryDTO`
- `Prediction1X2DTO`
- `OUPredictionDTO`
- `ComboTicketDTO`
- `ComboLegDTO`
- `RecentResultDTO`
- `PerformanceSummaryDTO`

The API returns explicit DTOs, never raw SQLAlchemy models.

## Frontend Recommendations

- Treat nullable fields as expected states, not errors.
- Display confidence as probability quality/value/risk, not result certainty.
- Hide ROI until `performance.summary.roi` is non-null and documented as reliable.
- Keep no-bet states visible and understandable.
- Use `kickoff_at_paris` for French user-facing calendars.
- Use `warnings_public` only; never expect staff warning internals.
- Implement loading/empty/error states for every list endpoint.
- Cache short-lived read responses on the dashboard server if needed.

## Errors To Handle

- `401`: missing or invalid API token.
- `403`: API disabled or not read-only.
- `404`: fixture, competition, prediction or combo not found.
- `422`: invalid query parameter, date or limit.
- `500`: masked server error; do not display internals.

## Explicit Non-Goals For The Dashboard

The dashboard must not:

- recalculate predictions;
- call API-Football;
- infer hidden staff-only warnings;
- mutate combo tickets;
- run settlement;
- publish Discord;
- expose the API token in browser JavaScript.

Use `docs/web_api_contract.md` for the full contract and `reports/web_api_v1_readiness.md` for the readiness decision.
