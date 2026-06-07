# FootLumen API Security

The V1 API is disabled and token-protected by default. It is intended as a shadow read-only service before any dashboard integration.

## Environment

```env
FOOTLUMEN_API_ENABLED=false
FOOTLUMEN_API_READ_ONLY=true
FOOTLUMEN_API_REQUIRE_TOKEN=true
FOOTLUMEN_API_TOKEN=
FOOTLUMEN_API_CORS_ORIGINS=
FOOTLUMEN_API_DOCS_ENABLED=false
FOOTLUMEN_API_PUBLIC_BASE_URL=
```

`FOOTLUMEN_API_TOKEN` must be supplied through the environment or a local ignored `.env`; it must never be committed, printed or logged.

## Authentication

When enabled, requests authenticate with either:

```http
Authorization: Bearer <token>
X-FootLumen-Api-Key: <token>
```

Missing or invalid tokens return `401`. Disabled API returns `403`. Error messages are generic and never echo the supplied token.

## Read-Only Guarantees

Routes must only open read sessions and must never commit. Endpoints must not call API-Football, publish Discord, recalculate predictions, settle tickets, mutate combo tickets or expose raw payloads.

The test suite includes global checks for:

- no `session.add`, `session.delete` or `session.commit`;
- unchanged row counts on key tables after API calls;
- no `payload_json`, webhook, token, secret or raw snapshot strings in API responses.

## CORS And Docs

CORS is closed by default. Set `FOOTLUMEN_API_CORS_ORIGINS` to explicit origins only, for example `https://app.footlumen.com`. Wildcard `*` is ignored by the app.

OpenAPI/Swagger are disabled by default with `FOOTLUMEN_API_DOCS_ENABLED=false`. Enable docs only in a controlled development or internal shadow environment.

## Logging

API request logs include path, method, status, duration and client IP. They do not log query strings, authorization headers, API keys or response bodies.

## Rate Limiting

Rate limiting is handled at the reverse proxy layer. See `deploy/nginx/api.footlumen.com.conf.example` for an Nginx `limit_req` example.

## Deployment Preview

Production should run behind Nginx or another reverse proxy, bound locally:

```bash
uvicorn football_predictor.web_api.app:app --host 127.0.0.1 --port 8000
```

Use `docs/web_api_deployment.md` for systemd, Nginx, HTTPS, smoke tests, rollback and token rotation.
