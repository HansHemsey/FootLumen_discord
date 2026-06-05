# Release Main Public Ready Report

Date UTC: 2026-06-05

## Summary

- Source branch: `production/public-ready-cdm-2026`
- Target branch: `main`
- Release SHA before merge: `0a0f87b`
- Main SHA before merge: `54d7293`
- Remote: `origin https://github.com/HansHemsey/soccer-pronos.git`
- Status: `READY_WITH_WARNINGS`

No blocker was found. The release is ready to merge into `main` if the final
post-merge checks remain green. Public combo publication must remain disabled by
configuration until a staff-only shadow period is validated.

## Git And Security Audit

Commands run:

```bash
git status --short
git branch --show-current
git remote -v
git log --oneline --decorate -5
git fetch origin --prune
git for-each-ref --format='%(refname:short) %(objectname:short)' \
  refs/heads/main \
  refs/heads/production/public-ready-cdm-2026 \
  refs/remotes/origin/main \
  refs/remotes/origin/production/public-ready-cdm-2026
git log --oneline origin/main..origin/production/public-ready-cdm-2026
git diff --stat origin/main...origin/production/public-ready-cdm-2026
git ls-files | rg '(^|/)\.env($|\.)|\.secrets\.yaml$|config/.*\.local\.yaml$|\.claude/settings\.local\.json$|^logs/|\.db$|discord_webhooks\.local\.yaml' || true
make security
```

Results:

- Worktree clean before release checks.
- Local and remote release refs aligned at `0a0f87b`.
- Local and remote main refs aligned at `54d7293`.
- Sensitive tracked file scan returned only `.env.example`.
- `make security` passed.

## Checks Run

| Check | Result | Notes |
| --- | --- | --- |
| `.venv/bin/python -m compileall src tests scripts alembic` | OK | No syntax errors. |
| `.venv/bin/python -m ruff check .` | OK | Lint clean. |
| `.venv/bin/python -m mypy src` | OK | Type check clean. |
| `.venv/bin/python -m pytest` | OK | `587 passed`, 1 local joblib/loky CPU warning. |
| `make check` | OK | Compile, ruff, mypy, security and pytest passed. |
| `make security` | OK | No obvious credentials found in versioned files. |

## Dry Runs Run

| Dry-run | Result | Notes |
| --- | --- | --- |
| `football-predictor healthcheck` | OK with warning | Secrets masked; local DB reports missing tables. |
| `football-predictor doctor --strict` | OK with warning | Same local DB warning. |
| `scripts/worldcup_coverage_report.py` | OK | 72 fixtures; fixtures/standings present; dynamic coverage currently 0%. |
| `scripts/dry_run_worldcup_combo_candidates.py` | OK | 37 sessions, 0 candidates. |
| `scripts/dry_run_worldcup_combo_builder.py` | OK | 0 tickets. |
| `football-predictor worldcup-combos-run --dry-run` | OK | 0 persisted tickets. |
| `scripts/lock_worldcup_combos.py` | OK | Safe dry-run no-op; combo tables missing locally. |
| `football-predictor worldcup-combos-publish --dry-run` | OK | Safe dry-run no-op; no Discord publication. |
| `scripts/settle_worldcup_combos.py` | OK | Safe dry-run no-op; combo tables missing locally. |
| `scripts/backtest_ou_v2_publication.py --dry-run` | OK | 766 rows after filters; reports not written. |

Warnings:

- Local DB is not migrated to combo/enrichment schema, so combo lock/publish/settle
  dry-runs report missing combo tables.
- Local World Cup dynamic coverage is not production-ready: odds, predictions,
  lineups, injuries, statistics, events and player statistics are currently 0%.
- O/U backtest dry-run emitted non-blocking Arrow CPU-info warnings in this
  sandbox.

## Migrations Detected

The VPS must run `alembic upgrade head` before execute-mode combo jobs:

- `alembic/versions/0006_world_cup_combo_tables.py`
- `alembic/versions/0007_combo_persistence_hardening.py`
- `alembic/versions/0008_api_coverage_observations.py`
- `alembic/versions/0009_worldcup_enrichment_tables.py`

Expected new production tables include:

- `combo_tickets`
- `combo_ticket_legs`
- `combo_ticket_snapshots`
- `api_coverage_observations`
- `national_team_aliases`
- `national_team_matches`
- `national_elo_snapshots`
- `fifa_ranking_snapshots`
- `worldcup_group_state_snapshots`
- `squad_strength_features`

## Production Configs To Verify On VPS

- `.env` exists and is not overwritten.
- `API_FOOTBALL_KEY` is set.
- `DATABASE_URL` points to the intended production DB.
- `DISCORD_WEBHOOKS_CONFIG_PATH` points to the local non-versioned webhook config.
- `DISCORD_CHANNELS_CONFIG_PATH` points to the expected channels config.
- `WORLD_CUP_COMBOS_CONFIG_PATH=config/worldcup_combos.yaml`.
- `config/worldcup_combos.yaml` keeps:
  - `enabled: true`
  - `staff_only_shadow_mode: true`
  - `publish_no_bet_public: false`
  - `allow_public_matchday3: false`
  - `allow_public_knockout: false`
- `staff_channel_key` and `public_channel_key` match VPS Discord routing.
- `config/prod_worldcup.example.crontab` or `config/prod_worldcup.crontab` paths
  are adjusted to the VPS app directory.

## Merge Commands

Run only after this report is committed and pushed on the release branch:

```bash
git checkout main
git pull --ff-only origin main

git merge --no-ff production/public-ready-cdm-2026 \
  -m "merge: prepare CDM 2026 public-ready production release"

.venv/bin/python -m compileall src tests scripts alembic
.venv/bin/python -m pytest
make check
make security

git push origin main

TAG_NAME="cdm-2026-public-ready-$(date -u +%Y%m%d)"
git tag -a "$TAG_NAME" -m "CDM 2026 public-ready production release"
git push origin "$TAG_NAME"
git rev-parse --short HEAD
```

Do not delete `production/public-ready-cdm-2026`.

## VPS Deployment Commands

```bash
ssh <USER>@<VPS_HOST>

export APP_DIR="/opt/soccer-pronos"
export BRANCH="main"
export RELEASE_TAG="cdm-2026-public-ready-20260605"
export BACKUP_DIR="$HOME/soccer-pronos-backups/$(date -u +%Y%m%d-%H%M%S)"
export PYTHON_BIN="python3.11"
export DB_PATH="<DB_PATH>"
export DATABASE_URL="<DATABASE_URL>"
export PUBLIC_CHANNEL_KEY="<PUBLIC_CHANNEL_KEY>"
export STAFF_CHANNEL_KEY="<STAFF_CHANNEL_KEY>"

set -euo pipefail

mkdir -p "$BACKUP_DIR"
cd "$APP_DIR"

git rev-parse HEAD > "$BACKUP_DIR/current_sha.txt"
git status --short > "$BACKUP_DIR/git_status_before.txt"
crontab -l > "$BACKUP_DIR/crontab.before" 2>/dev/null || true
[ -f .env ] && cp .env "$BACKUP_DIR/env.before" || true

if [ "$DB_PATH" != "<DB_PATH>" ] && [ -f "$DB_PATH" ]; then
  cp "$DB_PATH" "$BACKUP_DIR/$(basename "$DB_PATH").before"
  [ -f "$DB_PATH-wal" ] && cp "$DB_PATH-wal" "$BACKUP_DIR/$(basename "$DB_PATH").wal.before" || true
  [ -f "$DB_PATH-shm" ] && cp "$DB_PATH-shm" "$BACKUP_DIR/$(basename "$DB_PATH").shm.before" || true
else
  echo "WARN: DB_PATH a renseigner pour backup DB."
fi

crontab -r 2>/dev/null || true

git fetch origin --prune
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-dev.txt
python scripts/repair_editable_install.py

python - <<'PY'
from pathlib import Path
from dotenv import dotenv_values

if not Path(".env").exists():
    raise SystemExit("ERROR: .env absent; ne pas ecraser avec .env.example.")

env = dotenv_values(".env")
for key in [
    "API_FOOTBALL_KEY",
    "DATABASE_URL",
    "APP_TIMEZONE",
    "DISCORD_WEBHOOKS_CONFIG_PATH",
    "DISCORD_CHANNELS_CONFIG_PATH",
    "WORLD_CUP_COMBOS_CONFIG_PATH",
]:
    print(f"{key}: {'set' if env.get(key) else 'MISSING'}")
PY

python - <<'PY'
import os
from pathlib import Path

path = Path("config/worldcup_combos.yaml")
text = path.read_text(encoding="utf-8")

def set_yaml_scalar(content: str, key: str, value: str) -> str:
    lines = content.splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            lines[i] = f"{key}: {value}"
            found = True
    if not found:
        lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"

text = set_yaml_scalar(text, "staff_channel_key", os.environ["STAFF_CHANNEL_KEY"])
text = set_yaml_scalar(text, "public_channel_key", os.environ["PUBLIC_CHANNEL_KEY"])
text = set_yaml_scalar(text, "staff_only_shadow_mode", "true")
text = set_yaml_scalar(text, "publish_no_bet_public", "false")
text = set_yaml_scalar(text, "allow_public_matchday3", "false")
text = set_yaml_scalar(text, "allow_public_knockout", "false")
path.write_text(text, encoding="utf-8")
PY

alembic current || true
alembic upgrade head
alembic current

python - <<'PY'
from sqlalchemy import create_engine, inspect
from football_predictor.config.settings import get_settings

engine = create_engine(get_settings().database_url)
tables = set(inspect(engine).get_table_names())
required = {
    "combo_tickets",
    "combo_ticket_legs",
    "combo_ticket_snapshots",
    "api_coverage_observations",
    "national_team_aliases",
    "national_team_matches",
    "national_elo_snapshots",
    "fifa_ranking_snapshots",
    "worldcup_group_state_snapshots",
    "squad_strength_features",
}
missing = sorted(required - tables)
print("missing_tables:", missing)
raise SystemExit(1 if missing else 0)
PY

football-predictor healthcheck
football-predictor doctor --strict
make security

PYTHONPATH=src .venv/bin/python scripts/worldcup_coverage_report.py --league-id 1 --season 2026
PYTHONPATH=src .venv/bin/python scripts/dry_run_worldcup_combo_candidates.py --config config/worldcup_combos.yaml
PYTHONPATH=src .venv/bin/python scripts/dry_run_worldcup_combo_builder.py --config config/worldcup_combos.yaml
football-predictor worldcup-combos-run --config config/worldcup_combos.yaml --dry-run
PYTHONPATH=src .venv/bin/python scripts/lock_worldcup_combos.py --config config/worldcup_combos.yaml
football-predictor worldcup-combos-publish --config config/worldcup_combos.yaml --dry-run
PYTHONPATH=src .venv/bin/python scripts/settle_worldcup_combos.py --config config/worldcup_combos.yaml

cp config/prod_worldcup.example.crontab /tmp/prod_worldcup.crontab
python - <<'PY'
import os
from pathlib import Path

path = Path("/tmp/prod_worldcup.crontab")
text = path.read_text(encoding="utf-8")
text = text.replace("/opt/football-predictor/app", os.environ["APP_DIR"])
if "CRON_TZ=" not in text:
    text = "CRON_TZ=Europe/Paris\n" + text
path.write_text(text, encoding="utf-8")
PY

sed -n '1,120p' /tmp/prod_worldcup.crontab
crontab /tmp/prod_worldcup.crontab
crontab -l

mkdir -p logs/cron
tail -n 80 logs/cron/worldcup_late.log 2>/dev/null || true
tail -n 80 logs/cron/worldcup_combos_publish.log 2>/dev/null || true

python - <<'PY'
from sqlalchemy import create_engine, text
from football_predictor.config.settings import get_settings

engine = create_engine(get_settings().database_url)
with engine.connect() as conn:
    for query in [
        "select status, count(*) from combo_tickets group by status",
        "select message_type, status, count(*) from discord_messages group by message_type, status",
    ]:
        print("\\n--", query)
        for row in conn.execute(text(query)):
            print(tuple(row))
PY

echo "DEPLOYMENT_DONE"
echo "SHA=$(git rev-parse --short HEAD)"
echo "TAG=$RELEASE_TAG"
```

## Rollback

Restore crons:

```bash
crontab -r 2>/dev/null || true
if [ -f "$BACKUP_DIR/crontab.before" ]; then
  crontab "$BACKUP_DIR/crontab.before"
fi
```

Rollback code:

```bash
cd "$APP_DIR"
OLD_SHA="$(cat "$BACKUP_DIR/current_sha.txt")"
git fetch origin --prune
git checkout "$OLD_SHA"
python -m pip install -r requirements-dev.txt
python scripts/repair_editable_install.py
football-predictor healthcheck
```

Rollback SQLite DB if migration fails:

```bash
crontab -r 2>/dev/null || true

if [ "$DB_PATH" != "<DB_PATH>" ] && [ -f "$BACKUP_DIR/$(basename "$DB_PATH").before" ]; then
  cp "$BACKUP_DIR/$(basename "$DB_PATH").before" "$DB_PATH"
fi

if [ "$DB_PATH" != "<DB_PATH>" ] && [ -f "$BACKUP_DIR/$(basename "$DB_PATH").wal.before" ]; then
  cp "$BACKUP_DIR/$(basename "$DB_PATH").wal.before" "$DB_PATH-wal"
fi

if [ "$DB_PATH" != "<DB_PATH>" ] && [ -f "$BACKUP_DIR/$(basename "$DB_PATH").shm.before" ]; then
  cp "$BACKUP_DIR/$(basename "$DB_PATH").shm.before" "$DB_PATH-shm"
fi

football-predictor healthcheck
```

## 24h Monitoring

- Cron failures in `worldcup_*` logs.
- Repeated `odds_missing`, `odds_stale`, `lineup_risk_too_high`.
- No public combo publication while `staff_only_shadow_mode: true`.
- No duplicated Discord messages.
- Combo snapshots `generated`, `pre_lock`, `published`, `settled`.
- CDM coverage for odds, predictions and lineups.
