#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ -n "${FOOTBALL_PREDICTOR_BIN:-}" ]; then
  CLI_BIN="$FOOTBALL_PREDICTOR_BIN"
elif [ -x "$ROOT_DIR/scripts/football_predictor_cli.sh" ]; then
  CLI_BIN="$ROOT_DIR/scripts/football_predictor_cli.sh"
else
  CLI_BIN="football-predictor"
fi

if [ ! -f ".env" ]; then
  echo "Missing .env. Create it from .env.example and fill local secrets outside Git." >&2
  exit 1
fi

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

mkdir -p data/raw data/processed data/models

"$CLI_BIN" init-db
"$CLI_BIN" doctor --strict
