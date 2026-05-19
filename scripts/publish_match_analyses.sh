#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"
CLI_BIN="$(resolve_cli_bin)"
RUN_DATE="${DATE:-$(default_run_date)}"
CONFIG_PATH="${CONFIG:-config/competitions.yaml}"
MODEL_DIR="${MODEL_DIR:-data/models/v1}"
REFRESH_DATA="${REFRESH_DATA:-false}"
SEND_DISCORD="${SEND_DISCORD:-false}"
DRY_RUN="${DRY_RUN:-true}"
PRINT_ONLY="${PRINT_ONLY:-false}"
FORCE="${FORCE:-false}"
SAVE_RAW="${SAVE_RAW:-true}"
ANALYSIS_GRACE_MINUTES="${ANALYSIS_GRACE_MINUTES:-45}"
REPORT_DIR="${REPORT_DIR:-reports/daily}"
RUN_ID="${RUN_ID:-$(date -u +%H%M%S)}"
SUMMARY_PATH="${JSON_OUTPUT:-$REPORT_DIR/${RUN_DATE}_analyses_${RUN_ID}_summary.json}"

mkdir -p "$REPORT_DIR" data/raw data/processed data/models

PUBLISH_DRY_RUN="$DRY_RUN"
if ! bool_flag "$SEND_DISCORD"; then
  PUBLISH_DRY_RUN="true"
fi

set -- publish-match-analyses \
  --date "$RUN_DATE" \
  --config "$CONFIG_PATH" \
  --model-dir "$MODEL_DIR" \
  --analysis-grace-minutes "$ANALYSIS_GRACE_MINUTES" \
  --json \
  --json-output "$SUMMARY_PATH"

if bool_flag "$REFRESH_DATA"; then
  set -- "$@" --refresh-data
else
  set -- "$@" --no-refresh-data
fi

if bool_flag "$SAVE_RAW"; then
  set -- "$@" --save-raw
fi

if bool_flag "$PUBLISH_DRY_RUN"; then
  set -- "$@" --dry-run
fi

if bool_flag "$PRINT_ONLY"; then
  set -- "$@" --print-only
fi

if bool_flag "$FORCE"; then
  set -- "$@" --force
fi

if [ -n "${LIMIT:-}" ]; then
  set -- "$@" --limit "$LIMIT"
fi

"$CLI_BIN" "$@"
echo "Match analyses summary written to $SUMMARY_PATH"
