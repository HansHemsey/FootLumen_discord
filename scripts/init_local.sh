#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

CLI_BIN="${FOOTBALL_PREDICTOR_BIN:-football-predictor}"

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
