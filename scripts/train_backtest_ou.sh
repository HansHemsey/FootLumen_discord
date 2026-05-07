#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"
CLI_BIN="$(resolve_cli_bin)"
CONFIG_PATH="${CONFIG:-}"
if [ -z "$CONFIG_PATH" ]; then
  if [ -f "config/competitions_history.yaml" ]; then
    CONFIG_PATH="config/competitions_history.yaml"
  else
    CONFIG_PATH="config/competitions.yaml"
  fi
fi
DATASET="${DATASET:-data/processed/training_ou_v1.parquet}"
MODEL_DIR="${MODEL_DIR:-data/models/ou-v1}"
BACKTEST_DIR="${BACKTEST_DIR:-reports/backtest_ou_v1}"
MODEL_VERSION="${MODEL_VERSION:-ou-v1}"
N_SPLITS="${N_SPLITS:-5}"

mkdir -p "$(dirname "$DATASET")" "$MODEL_DIR" "$BACKTEST_DIR"

COMPETITION_ARGS="$(competition_dataset_args_ou "$CONFIG_PATH")"

if [ -z "$COMPETITION_ARGS" ]; then
  echo "No enabled competitions found in $CONFIG_PATH" >&2
  exit 1
fi

echo "Training O/U config=$CONFIG_PATH dataset=$DATASET model_dir=$MODEL_DIR"

set -- ou build-dataset
# shellcheck disable=SC2086
set -- "$@" $COMPETITION_ARGS --output "$DATASET"
if [ -n "${LIMIT:-}" ]; then
  set -- "$@" --limit "$LIMIT"
fi
"$CLI_BIN" "$@"

"$CLI_BIN" ou train \
  --dataset "$DATASET" \
  --output-dir "$MODEL_DIR" \
  --version "$MODEL_VERSION"

"$CLI_BIN" ou backtest \
  --dataset "$DATASET" \
  --output-dir "$BACKTEST_DIR" \
  --n-splits "$N_SPLITS"
