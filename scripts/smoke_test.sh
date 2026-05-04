#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

LIVE_MODE="${SMOKE_LIVE:-false}"

if [ -n "${FOOTBALL_PREDICTOR_BIN:-}" ]; then
  run_cli() {
    "$FOOTBALL_PREDICTOR_BIN" "$@"
  }
elif [ -x ".venv/bin/python" ]; then
  run_cli() {
    PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}src" .venv/bin/python -m football_predictor.cli "$@"
  }
elif command -v football-predictor >/dev/null 2>&1; then
  run_cli() {
    football-predictor "$@"
  }
else
  echo "Missing football-predictor command. Run make install or create .venv first." >&2
  exit 1
fi

usage() {
  cat <<'USAGE'
Usage: scripts/smoke_test.sh [--live]

Default mode is local-only:
  - no API-Football call
  - no Discord send
  - SQLite DB under data/smoke/
  - predict-today dry-run

Live mode is explicit:
  SMOKE_LIVE=true scripts/smoke_test.sh --live
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --live)
      LIVE_MODE="true"
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

for path in \
  docs/api_football_reference.md \
  docs/api_football_reference.json \
  docs/api_football_players_reference.md \
  docs/api_football_players_reference.json \
  docs/api_football_players_cache.json
do
  if [ ! -f "$path" ]; then
    echo "Missing required reference file: $path" >&2
    exit 1
  fi
done

mkdir -p data/smoke data/raw data/processed data/models

export DATABASE_URL="${SMOKE_DATABASE_URL:-sqlite:///./data/smoke/football_predictor_smoke.db}"
export API_FOOTBALL_REFERENCE_PATH="${API_FOOTBALL_REFERENCE_PATH:-docs/api_football_reference.json}"
export API_FOOTBALL_PLAYERS_REFERENCE_PATH="${API_FOOTBALL_PLAYERS_REFERENCE_PATH:-docs/api_football_players_reference.json}"
export API_FOOTBALL_PLAYERS_CACHE_PATH="${API_FOOTBALL_PLAYERS_CACHE_PATH:-docs/api_football_players_cache.json}"

run_cli init-db
run_cli seed-reference-from-docs \
  --reference "$API_FOOTBALL_REFERENCE_PATH" \
  --players "$API_FOOTBALL_PLAYERS_REFERENCE_PATH"
run_cli doctor --strict
run_cli data-quality

RUN_DATE="${SMOKE_DATE:-$(date +%F)}"
RUN_WINDOW="${SMOKE_WINDOW:-now}"
RUN_LIMIT="${SMOKE_LIMIT:-5}"

set -- predict-today --date "$RUN_DATE" --window "$RUN_WINDOW" --dry-run --json --limit "$RUN_LIMIT"

if [ -n "${SMOKE_LEAGUE_ID:-}" ]; then
  set -- "$@" --league "$SMOKE_LEAGUE_ID"
fi

if [ -n "${SMOKE_SEASON:-}" ]; then
  set -- "$@" --season "$SMOKE_SEASON"
fi

if [ "$LIVE_MODE" = "true" ]; then
  if [ -z "${API_FOOTBALL_KEY:-}" ]; then
    echo "SMOKE_LIVE=true requires API_FOOTBALL_KEY in the environment." >&2
    exit 1
  fi
  set -- "$@" --refresh-data --save-raw
  if [ "${SMOKE_SEND_DISCORD:-false}" = "true" ]; then
    set -- "$@" --send-discord
  fi
  if [ "${SMOKE_PRINT_ONLY:-false}" = "true" ]; then
    set -- "$@" --print-only
  fi
else
  set -- "$@" --no-refresh-data
fi

run_cli "$@"

if [ -n "${SMOKE_FIXTURE_ID:-}" ]; then
  if [ "$LIVE_MODE" = "true" ]; then
    run_cli predict --fixture "$SMOKE_FIXTURE_ID" --refresh-data --save-raw --json
  else
    run_cli predict --fixture "$SMOKE_FIXTURE_ID" --no-refresh --json
  fi
fi

echo "Smoke test completed. live=$LIVE_MODE database=$DATABASE_URL"
