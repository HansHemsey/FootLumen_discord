#!/bin/sh
# Weekly ingestion: prepare upcoming fixtures for the next 7 local dates.
#
# Usage:
#   scripts/weekly_ingestion.sh
#   DATE=2026-05-04 scripts/weekly_ingestion.sh
#
# Environment variables:
#   DATE       first local date to ingest (default: today in Europe/Paris)
#   CONFIG     competitions config (default: config/competitions.yaml)
#   DRY_RUN    true/false, pass --dry-run to CLI (default: false)
#   SAVE_RAW   true/false, save raw API payloads (default: true)
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"
CLI_BIN="$(resolve_cli_bin)"
RUN_DATE="${DATE:-$(default_run_date)}"
CONFIG_PATH="${CONFIG:-config/competitions.yaml}"
DRY_RUN="${DRY_RUN:-false}"
SAVE_RAW="${SAVE_RAW:-true}"

run_optional() {
  label="$1"
  shift
  echo "$label"
  if ! "$@"; then
    echo "Warning: $label failed; continuing weekly ingestion." >&2
  fi
}

date_plus_days() {
  "$PYTHON_BIN" - "$RUN_DATE" "$1" <<'PY'
from datetime import date, timedelta
import sys

start = date.fromisoformat(sys.argv[1])
offset = int(sys.argv[2])
print((start + timedelta(days=offset)).isoformat())
PY
}

echo "Weekly fixture ingestion J+7 from date=$RUN_DATE config=$CONFIG_PATH"

enabled_competitions "$CONFIG_PATH" | while IFS="$(printf '\t')" read -r league_id season competition_key; do
  [ -n "$league_id" ] || continue
  offset=0
  while [ "$offset" -lt 7 ]; do
    fixture_date="$(date_plus_days "$offset")"
    set -- ingest-fixtures \
      --date "$fixture_date" \
      --league "$league_id" \
      --season "$season" \
      --refresh-api
    if bool_flag "$SAVE_RAW"; then
      set -- "$@" --save-raw
    fi
    if bool_flag "$DRY_RUN"; then
      set -- "$@" --dry-run
    fi
    run_optional \
      "Ingesting upcoming fixtures date=$fixture_date competition=$competition_key league=$league_id season=$season" \
      "$CLI_BIN" "$@"
    offset=$((offset + 1))
  done
done

echo "Weekly fixture ingestion complete for start_date=$RUN_DATE"
