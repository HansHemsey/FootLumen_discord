#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"
CLI_BIN="$(resolve_cli_bin)"
RUN_DATE="${DATE:-$(default_run_date)}"
RUN_WINDOW="${WINDOW:-now}"
REFRESH_DATA="${REFRESH_DATA:-false}"
SEND_DISCORD="${SEND_DISCORD:-false}"
DRY_RUN="${DRY_RUN:-true}"
PRINT_ONLY="${PRINT_ONLY:-false}"
FORCE="${FORCE:-false}"

set -- predict-today --date "$RUN_DATE" --window "$RUN_WINDOW"

if [ -n "${LEAGUE_ID:-}" ]; then
  set -- "$@" --league "$LEAGUE_ID"
fi

if [ -n "${SEASON:-}" ]; then
  set -- "$@" --season "$SEASON"
fi

if [ -n "${MODEL_DIR:-}" ]; then
  set -- "$@" --model-dir "$MODEL_DIR"
fi

if [ -n "${CONFIG:-}" ]; then
  set -- "$@" --config "$CONFIG"
fi

if [ -n "${LIMIT:-}" ]; then
  set -- "$@" --limit "$LIMIT"
fi

if [ "$REFRESH_DATA" = "true" ]; then
  set -- "$@" --refresh-data
else
  set -- "$@" --no-refresh-data
fi

if [ "$SEND_DISCORD" = "true" ]; then
  set -- "$@" --send-discord
fi

if [ "$DRY_RUN" = "true" ]; then
  set -- "$@" --dry-run
fi

if [ "$PRINT_ONLY" = "true" ]; then
  set -- "$@" --print-only
fi

if [ "$FORCE" = "true" ]; then
  set -- "$@" --force
fi

"$CLI_BIN" "$@"
