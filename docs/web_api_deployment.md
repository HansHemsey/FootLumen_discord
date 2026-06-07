# FootLumen API V1 Shadow Deployment

This runbook prepares `api.footlumen.com` for the read-only API V1. The API reads data already produced by existing jobs. It must not run crons, publish Discord, call API-Football, settle tickets or write to the database.

## Environment Variables

Add these values to the local ignored `.env` or to the systemd `EnvironmentFile`:

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

Never print the token in logs. Keep `FOOTLUMEN_API_DOCS_ENABLED=false` for shadow production.

## Local Smoke

```bash
source .venv/bin/activate
FOOTLUMEN_API_ENABLED=true FOOTLUMEN_API_TOKEN=dev-token \
uvicorn football_predictor.web_api.app:app --reload --host 127.0.0.1 --port 8000

FOOTLUMEN_API_BASE_URL=http://127.0.0.1:8000 \
FOOTLUMEN_API_TOKEN=dev-token \
bash scripts/smoke_api_v1.sh
```

## Production Uvicorn

Run Uvicorn bound to localhost only:

```bash
cd /opt/football-predictor/app
source .venv/bin/activate
uvicorn football_predictor.web_api.app:app --host 127.0.0.1 --port 8000
```

The API service is separate from cron. Installing or restarting it must not touch existing crontabs.

## Systemd

Copy the example and adjust paths:

```bash
sudo cp deploy/systemd/footlumen-api.service.example /etc/systemd/system/footlumen-api.service
sudo systemctl daemon-reload
sudo systemctl enable footlumen-api
sudo systemctl start footlumen-api
sudo systemctl status footlumen-api --no-pager
```

Logs:

```bash
journalctl -u footlumen-api --since "30 min ago" --no-pager
```

## Nginx Reverse Proxy

Copy the example and adjust host/certificate paths if needed:

```bash
sudo cp deploy/nginx/api.footlumen.com.conf.example /etc/nginx/sites-available/api.footlumen.com.conf
sudo ln -s /etc/nginx/sites-available/api.footlumen.com.conf /etc/nginx/sites-enabled/api.footlumen.com.conf
sudo nginx -t
sudo systemctl reload nginx
```

Rate limiting is configured at Nginx level in the example. Keep it there rather than using a per-process in-memory limiter.

## HTTPS

Use Let's Encrypt after DNS points `api.footlumen.com` to the VPS:

```bash
sudo certbot --nginx -d api.footlumen.com
sudo nginx -t
sudo systemctl reload nginx
```

## Healthcheck

```bash
curl -fsS -H "Authorization: Bearer $FOOTLUMEN_API_TOKEN" \
  https://api.footlumen.com/api/v1/health
```

Expected: `status=ok`, `read_only=true`, `database_ok=true`.

## Token Rotation

1. Generate a new token outside the repo.
2. Update the ignored environment file or systemd secret source.
3. Restart the API service.
4. Smoke test with the new token.
5. Remove the old token from clients.

```bash
sudo systemctl restart footlumen-api
FOOTLUMEN_API_BASE_URL=https://api.footlumen.com bash scripts/smoke_api_v1.sh
```

## API Disabled

Emergency disable:

```env
FOOTLUMEN_API_ENABLED=false
```

Then restart:

```bash
sudo systemctl restart footlumen-api
```

Requests should return `403 api_disabled`.

## Rollback

```bash
cd /opt/football-predictor/app
git fetch origin --prune
git checkout <OLD_SHA>
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/repair_editable_install.py
sudo systemctl restart footlumen-api
curl -fsS -H "Authorization: Bearer $FOOTLUMEN_API_TOKEN" \
  http://127.0.0.1:8000/api/v1/health
```

If rollback is due to an API issue, disable the API first, then restore code.
