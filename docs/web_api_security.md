# FootLumen API Security

The V1 API is disabled and token-protected by default. It is intended as a shadow read-only service before any dashboard integration.

## Environment

```env
FOOTLUMEN_API_ENABLED=false
FOOTLUMEN_API_READ_ONLY=true
FOOTLUMEN_API_REQUIRE_TOKEN=true
FOOTLUMEN_API_TOKEN=
FOOTLUMEN_API_CORS_ORIGINS=
FOOTLUMEN_API_PUBLIC_BASE_URL=
```

`FOOTLUMEN_API_TOKEN` must be supplied through the environment or a local ignored `.env`; it must never be committed or logged.

## Authentication

When enabled, requests authenticate with either:

```http
Authorization: Bearer <token>
X-FootLumen-Api-Key: <token>
```

Missing or invalid tokens return `401`. Disabled API returns `403`.

## Read-Only Guarantees

Routes must only open read sessions and must never commit. Endpoints must not call API-Football, publish Discord, recalculate predictions, settle tickets, mutate combo tickets or expose raw payloads.

## Deployment Preview

Production should run behind Nginx or another reverse proxy, bound locally:

```bash
uvicorn football_predictor.web_api.app:app --host 127.0.0.1 --port 8000
```

CORS is closed by default. Add only explicit dashboard origins, for example `https://app.footlumen.com`, when the dashboard is ready.
