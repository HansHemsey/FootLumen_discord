#!/bin/sh
# Daily O/U 2.5 pipeline: ingest market odds then run predictions.
#
# Usage:
#   scripts/daily_ou.sh                          # dry-run, no Discord
#   SEND_DISCORD=true DRY_RUN=false scripts/daily_ou.sh
#
# Environment variables (all optional):
#   DATE             YYYY-MM-DD to process (default: today in Europe/Paris)
#   CONFIG           path to competitions.yaml (default: config/competitions.yaml)
#   MODEL_DIR        path to ou model dir (default: data/models/ou-v1)
#   REFRESH_DATA     true/false — ingest O/U odds before predicting (default: true)
#   SEND_DISCORD     true/false — actually fire Discord webhooks (default: false)
#   DRY_RUN          true/false — skip writes if true (default: true)
#   PRINT_ONLY       true/false — print Discord messages without sending (default: false)
#   SAVE_RAW         true/false — save raw API payloads (default: true)
#   EDGE_THRESHOLD   min edge to display (default: 0.02)
#   REPORT_DIR       directory for JSON summaries (default: reports/daily)
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"
CLI_BIN="$(resolve_cli_bin)"
RUN_DATE="${DATE:-$(default_run_date)}"
CONFIG_PATH="${CONFIG:-config/competitions.yaml}"
MODEL_DIR="${MODEL_DIR:-data/models/ou-v1}"
REFRESH_DATA="${REFRESH_DATA:-true}"
SEND_DISCORD="${SEND_DISCORD:-false}"
DRY_RUN="${DRY_RUN:-true}"
PRINT_ONLY="${PRINT_ONLY:-false}"
SAVE_RAW="${SAVE_RAW:-true}"
EDGE_THRESHOLD="${EDGE_THRESHOLD:-0.02}"
REPORT_DIR="${REPORT_DIR:-reports/daily}"
SUMMARY_PATH="${JSON_OUTPUT:-$REPORT_DIR/${RUN_DATE}_ou_summary.json}"

mkdir -p "$REPORT_DIR" data/raw data/processed data/models

run_optional() {
  label="$1"
  shift
  echo "$label"
  if ! "$@"; then
    echo "Warning: $label failed; continuing O/U daily pipeline." >&2
  fi
}

# --- 1. Ingest O/U odds for each enabled competition ---
if bool_flag "$REFRESH_DATA"; then
  enabled_competitions "$CONFIG_PATH" | while IFS="$(printf '\t')" read -r league_id season competition_key; do
    [ -n "$league_id" ] || continue
    ou_odds_cmd="ou ingest-odds --date $RUN_DATE --league-id $league_id --season $season"
    run_optional \
      "Ingesting O/U odds date=$RUN_DATE competition=$competition_key league=$league_id season=$season" \
      "$CLI_BIN" $ou_odds_cmd
  done
fi

# --- 2. Run O/U predictions ---
PUBLISH_DRY_RUN="$DRY_RUN"
if ! bool_flag "$SEND_DISCORD"; then
  PUBLISH_DRY_RUN="true"
fi

set -- ou run-daily \
  --date "$RUN_DATE" \
  --edge-threshold "$EDGE_THRESHOLD"

if [ -f "$MODEL_DIR/model.joblib" ]; then
  set -- "$@" --model-dir "$MODEL_DIR"
fi

if bool_flag "$SEND_DISCORD"; then
  set -- "$@" --send-discord
fi

if bool_flag "$PUBLISH_DRY_RUN"; then
  set -- "$@" --dry-run
fi

if bool_flag "$PRINT_ONLY"; then
  set -- "$@" --print-only
fi

if [ -n "${LIMIT:-}" ]; then
  set -- "$@" --limit "$LIMIT"
fi

if [ -n "${LEAGUE_ID:-}" ]; then
  set -- "$@" --league-id "$LEAGUE_ID"
fi

"$CLI_BIN" "$@" | tee "$SUMMARY_PATH"

echo "O/U daily pipeline complete for date=$RUN_DATE — summary at $SUMMARY_PATH"
