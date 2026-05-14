#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"
CLI_BIN="$(resolve_cli_bin)"
RUN_DATE="${DATE:-$(default_run_date)}"
RUN_WINDOW="${WINDOW:-late}"
CONFIG_PATH="${CONFIG:-config/competitions.yaml}"
PREDICTION_ENGINE="${PREDICTION_ENGINE:-v3}"
DEFAULT_V2_MODEL_DIR="data/models/v2-late"
DEFAULT_V2_ROLLBACK_MODEL_DIR="$DEFAULT_V2_MODEL_DIR"
if [ ! -f "$DEFAULT_V2_ROLLBACK_MODEL_DIR/model.joblib" ]; then
  DEFAULT_V2_ROLLBACK_MODEL_DIR="data/models/v1"
fi
DEFAULT_V3_MODEL_DIR="data/models/v3"
if [ "$PREDICTION_ENGINE" = "v2" ]; then
  MODEL_DIR="${MODEL_DIR:-$DEFAULT_V2_ROLLBACK_MODEL_DIR}"
else
  MODEL_DIR="${MODEL_DIR:-$DEFAULT_V3_MODEL_DIR}"
fi
V2_MODEL_DIR="${V2_MODEL_DIR:-$DEFAULT_V2_MODEL_DIR}"
if [ "$PREDICTION_ENGINE" = "v3" ]; then
  ANALYSIS_MODEL_DIR="${ANALYSIS_MODEL_DIR:-$DEFAULT_V2_ROLLBACK_MODEL_DIR}"
else
  ANALYSIS_MODEL_DIR="${ANALYSIS_MODEL_DIR:-$MODEL_DIR}"
fi
REFRESH_DATA="${REFRESH_DATA:-true}"
SEND_DISCORD="${SEND_DISCORD:-false}"
DRY_RUN="${DRY_RUN:-true}"
PRINT_ONLY="${PRINT_ONLY:-false}"
FORCE="${FORCE:-false}"
SAVE_RAW="${SAVE_RAW:-true}"
PUBLISH_ANALYSES="${PUBLISH_ANALYSES:-false}"
PUBLISH_RESULTS="${PUBLISH_RESULTS:-false}"
ANALYSIS_GRACE_MINUTES="${ANALYSIS_GRACE_MINUTES:-15}"
REPORT_DIR="${REPORT_DIR:-reports/daily}"
SUMMARY_SUFFIX="$RUN_WINDOW"
if [ "$PREDICTION_ENGINE" = "v3" ]; then
  SUMMARY_SUFFIX="${RUN_WINDOW}_v3"
fi
SUMMARY_PATH="${JSON_OUTPUT:-$REPORT_DIR/${RUN_DATE}_${SUMMARY_SUFFIX}_summary.json}"

mkdir -p "$REPORT_DIR" data/raw data/processed data/models

if [ "$PREDICTION_ENGINE" = "v3" ]; then
  set -- predict-today-v3 \
    --date "$RUN_DATE" \
    --window "$RUN_WINDOW" \
    --config "$CONFIG_PATH" \
    --model-dir "$MODEL_DIR" \
    --v2-model-dir "$V2_MODEL_DIR" \
    --json \
    --json-output "$SUMMARY_PATH"
elif [ "$PREDICTION_ENGINE" = "v2" ]; then
  set -- predict-today \
    --date "$RUN_DATE" \
    --window "$RUN_WINDOW" \
    --config "$CONFIG_PATH" \
    --model-dir "$MODEL_DIR" \
    --json \
    --json-output "$SUMMARY_PATH"
else
  echo "Unsupported PREDICTION_ENGINE=$PREDICTION_ENGINE; expected v2 or v3" >&2
  exit 2
fi

if bool_flag "$REFRESH_DATA"; then
  set -- "$@" --refresh-data
else
  set -- "$@" --no-refresh-data
fi

if bool_flag "$SAVE_RAW"; then
  set -- "$@" --save-raw
fi

if bool_flag "$SEND_DISCORD"; then
  set -- "$@" --send-discord
fi

if bool_flag "$SEND_DISCORD" && ! bool_flag "$DRY_RUN" && ! bool_flag "$PRINT_ONLY"; then
  set -- "$@" --production-mode
fi

if bool_flag "$DRY_RUN"; then
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

if bool_flag "$PUBLISH_ANALYSES"; then
  DATE="$RUN_DATE" \
    CONFIG="$CONFIG_PATH" \
    MODEL_DIR="$ANALYSIS_MODEL_DIR" \
    REFRESH_DATA="$REFRESH_DATA" \
    SEND_DISCORD="$SEND_DISCORD" \
    DRY_RUN="$DRY_RUN" \
    PRINT_ONLY="$PRINT_ONLY" \
    FORCE="$FORCE" \
    SAVE_RAW="$SAVE_RAW" \
    ANALYSIS_GRACE_MINUTES="$ANALYSIS_GRACE_MINUTES" \
    scripts/publish_match_analyses.sh
fi

"$CLI_BIN" "$@"

if bool_flag "$PUBLISH_RESULTS"; then
  DATE="$RUN_DATE" \
    CONFIG="$CONFIG_PATH" \
    REFRESH_DATA="$REFRESH_DATA" \
    SEND_DISCORD="$SEND_DISCORD" \
    DRY_RUN="$DRY_RUN" \
    PRINT_ONLY="$PRINT_ONLY" \
    FORCE="$FORCE" \
    SAVE_RAW="$SAVE_RAW" \
    scripts/publish_match_results.sh
fi

echo "Daily late summary written to $SUMMARY_PATH"
