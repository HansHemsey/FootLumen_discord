#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"
CLI_BIN="$(resolve_cli_bin)"
CONFIG_PATH="${CONFIG:-config/competitions.yaml}"
DATASET="${DATASET:-data/processed/training_v2_late.parquet}"
MODEL_DIR="${MODEL_DIR:-data/models/v2-late}"
BACKTEST_DIR="${BACKTEST_DIR:-reports/backtest_v2_late}"
PREDICTION_WINDOW="${PREDICTION_WINDOW:-30m}"
MODEL_VERSION="${MODEL_VERSION:-v2-late}"
REPORT_FORMAT="${REPORT_FORMAT:-both}"
MIN_QUALITY="${MIN_QUALITY:-0}"

mkdir -p "$(dirname "$DATASET")" "$MODEL_DIR" "$BACKTEST_DIR"

COMPETITION_ARGS="$(competition_dataset_args "$CONFIG_PATH")"

if [ -z "$COMPETITION_ARGS" ]; then
  echo "No enabled competitions found in $CONFIG_PATH" >&2
  exit 1
fi

# shellcheck disable=SC2086
"$CLI_BIN" build-dataset \
  $COMPETITION_ARGS \
  --prediction-window "$PREDICTION_WINDOW" \
  --output "$DATASET" \
  --min-quality "$MIN_QUALITY"

"$CLI_BIN" train \
  --dataset "$DATASET" \
  --output-dir "$MODEL_DIR" \
  --model-version "$MODEL_VERSION"

"$CLI_BIN" backtest \
  --dataset "$DATASET" \
  --model-dir "$MODEL_DIR" \
  --output-dir "$BACKTEST_DIR" \
  --format "$REPORT_FORMAT" \
  --retrain-v2-model-version "$MODEL_VERSION"
