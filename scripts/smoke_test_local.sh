#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

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

if [ "${SMOKE_RUN_TESTS:-true}" = "true" ]; then
  if [ -x ".venv/bin/python" ]; then
    .venv/bin/python -m pytest
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m pytest
  else
    echo "Missing Python interpreter for pytest." >&2
    exit 1
  fi
fi

export SMOKE_LIVE=false
export SMOKE_DATABASE_URL="${SMOKE_DATABASE_URL:-sqlite:///./data/smoke/football_predictor_smoke_local.db}"

scripts/smoke_test.sh
