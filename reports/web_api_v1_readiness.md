# FootLumen API V1 Readiness Report

Date: 2026-06-07
Status: READY
Target consumer: FootLumen_app dashboard
API base path: /api/v1

## Decision

The FootLumen API V1 read-only surface is ready to be consumed by the future dashboard in shadow mode.

Recommended dashboard API base URL:

- Local: `http://127.0.0.1:8000/api/v1`
- Production shadow target: `https://api.footlumen.com/api/v1`

The dashboard can start integration against this API contract now, provided it sends a bearer token and treats all prediction data as read-only.

## Available Routes

All expected V1 routes are registered:

| Method | Route | Status |
| --- | --- | --- |
| GET | `/api/v1/health` | available |
| GET | `/api/v1/version` | available |
| GET | `/api/v1/competitions` | available |
| GET | `/api/v1/competitions/{competition_key}` | available |
| GET | `/api/v1/fixtures/today` | available |
| GET | `/api/v1/fixtures/upcoming` | available |
| GET | `/api/v1/fixtures/{fixture_id}` | available |
| GET | `/api/v1/predictions/latest` | available |
| GET | `/api/v1/predictions/{fixture_id}` | available |
| GET | `/api/v1/ou/latest` | available |
| GET | `/api/v1/ou/{fixture_id}` | available |
| GET | `/api/v1/combos/today` | available |
| GET | `/api/v1/combos/latest` | available |
| GET | `/api/v1/combos/{ticket_key}` | available |
| GET | `/api/v1/results/recent` | available |
| GET | `/api/v1/performance/summary` | available |

## Curl Examples

```bash
export FOOTLUMEN_API_BASE_URL="https://api.footlumen.com/api/v1"
export FOOTLUMEN_API_TOKEN="<REPLACE_WITH_TOKEN>"

curl -H "Authorization: Bearer $FOOTLUMEN_API_TOKEN"   "$FOOTLUMEN_API_BASE_URL/health"

curl -H "Authorization: Bearer $FOOTLUMEN_API_TOKEN"   "$FOOTLUMEN_API_BASE_URL/fixtures/today?competition_key=fifa_world_cup_2026"

curl -H "Authorization: Bearer $FOOTLUMEN_API_TOKEN"   "$FOOTLUMEN_API_BASE_URL/predictions/latest?limit=20&only_public=false"

curl -H "Authorization: Bearer $FOOTLUMEN_API_TOKEN"   "$FOOTLUMEN_API_BASE_URL/ou/latest?only_value_picks=true"

curl -H "Authorization: Bearer $FOOTLUMEN_API_TOKEN"   "$FOOTLUMEN_API_BASE_URL/combos/today?include_staff=false"
```

## Required Environment

API service:

```env
FOOTLUMEN_API_ENABLED=true
FOOTLUMEN_API_READ_ONLY=true
FOOTLUMEN_API_REQUIRE_TOKEN=true
FOOTLUMEN_API_TOKEN=<REPLACE_WITH_TOKEN>
FOOTLUMEN_API_CORS_ORIGINS=https://app.footlumen.com
FOOTLUMEN_API_DOCS_ENABLED=false
FOOTLUMEN_API_PUBLIC_BASE_URL=https://api.footlumen.com
DATABASE_URL=<DATABASE_URL>
APP_TIMEZONE=Europe/Paris
```

Dashboard app:

```env
FOOTLUMEN_API_BASE_URL=https://api.footlumen.com/api/v1
FOOTLUMEN_API_TOKEN=<SERVER_SIDE_TOKEN>
```

Do not expose `FOOTLUMEN_API_TOKEN` in browser bundles. Calls should go through a server-side proxy or server actions in the dashboard app.

## Tests Run

| Check | Result |
| --- | --- |
| Route inventory via FastAPI app | PASS |
| `python -m compileall src tests scripts alembic` | PASS |
| web API pytest suite | PASS, 50 passed |
| `scripts/smoke_api_v1.sh` against local Uvicorn | PASS |
| `make check` | PASS, 656 passed |
| `make security` via `make check` security scan | PASS |

Note: local smoke required running Uvicorn and curl outside the sandbox because binding to `127.0.0.1` is restricted in the Codex sandbox. No external deployment was performed.

## Read-Only Evidence

The API code and tests prove the read-only boundary:

- DB sessions are yielded by `get_read_only_session()` and always rolled back/closed.
- API tests monkeypatch `Session.add`, `Session.delete` and `Session.commit` and call all V1 data endpoints successfully.
- API tests compare row counts before/after calls on `fixtures`, `model_predictions`, `ou_model_predictions`, `combo_tickets`, `combo_ticket_legs` and `discord_messages`.
- No endpoint imports or invokes Discord publication services.
- No endpoint imports or invokes API-Football ingestion clients.
- No endpoint imports or invokes combo settlement; the test explicitly fails if `WorldCupComboSettlementService.settle_open_records` is called.
- Combo endpoints only read `combo_tickets` and `combo_ticket_legs`; they do not mutate statuses.
- Result endpoints compute lightweight summaries from existing fixtures/predictions only.

## Security Evidence

- API disabled returns `403 api_disabled`.
- Missing/invalid token returns `401` without echoing the supplied token.
- Bearer token and `X-FootLumen-Api-Key` are supported.
- CORS is closed by default; wildcard `*` is ignored.
- OpenAPI/Swagger are disabled by default with `FOOTLUMEN_API_DOCS_ENABLED=false`.
- Security headers are installed.
- Request logs include method, path, status, duration and IP only; no headers, query strings, bodies or tokens.
- Tests assert no response contains `payload_json`, `webhook`, `token`, `secret`, `raw_snapshot`, `raw_api` or seeded canary values.
- DTOs never return SQLAlchemy models directly.

## Data Contract Summary

Primary DTO families:

- `CompetitionSummary`: competition identity and display metadata.
- `FixtureSummaryDTO`: teams, kickoff UTC/Paris, status, venue and public flags.
- `Prediction1X2DTO`: 1X2 probabilities, confidence, public explanations and filtered warnings.
- `OUPredictionDTO`: O/U V2 forecast/value fields, edge/EV and no-bet metadata.
- `ComboTicketDTO`: ticket metrics, filtered warnings, public legs and nullable settlement summary.
- `RecentResultDTO`: finished fixture score with compact prediction and combo impact context.
- `PerformanceSummaryDTO`: safe counters only; ROI remains `null` until reliable.

Forbidden fields remain excluded:

- `payload_json`, `route_json`, `response_json`;
- raw API snapshots and feature snapshots;
- Discord routing/webhooks;
- API keys, DB URLs and tokens;
- staff-only warnings, tracebacks and internal debug notes.

## Known Limits

- No entitlement/Stripe split yet; V1 shadow exposes safe DTOs only.
- Performance `roi` is intentionally `null`; do not display ROI in the dashboard until a reliable betting ledger exists.
- Results use existing fixture scores and latest prediction rows; no recalculation is performed.
- OpenAPI docs should remain disabled in production shadow.
- Rate limiting is expected at Nginx level, not in-process.
- Some list endpoints return empty arrays if cron data has not populated the DB yet.

## Next Steps For FootLumen_app

1. Configure `FOOTLUMEN_API_BASE_URL=https://api.footlumen.com/api/v1`.
2. Store `FOOTLUMEN_API_TOKEN` server-side only.
3. Start with `/health`, `/version`, `/competitions`, `/fixtures/today`, `/fixtures/upcoming`.
4. Build prediction views from `/predictions/latest` and `/ou/latest`.
5. Build CDM combo widgets from `/combos/today` and `/combos/latest`.
6. Build recent result widgets from `/results/recent`.
7. Treat nullable fields as normal API states.
8. Never recalculate predictions client-side.

## VPS Action

No VPS change is required just to continue dashboard development locally against mocks or a local API.

VPS setup becomes useful when the dashboard needs a real shadow backend at `https://api.footlumen.com`. Use `docs/web_api_deployment.md` at that point:

- pull latest `main`;
- install dependencies;
- set API env vars;
- start `footlumen-api` systemd service;
- configure Nginx reverse proxy;
- run `scripts/smoke_api_v1.sh`.

Do not touch crons or Discord for this API deployment.

## Final Status

READY. The dashboard can start consuming this API contract in shadow mode.
