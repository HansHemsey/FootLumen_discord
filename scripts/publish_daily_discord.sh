#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"
CLI_BIN="$(resolve_cli_bin)"
RUN_DATE="${DATE:-$(default_run_date)}"
CONFIG_PATH="${CONFIG:-config/competitions.yaml}"
DRY_RUN="${DRY_RUN:-true}"
PRINT_ONLY="${PRINT_ONLY:-false}"
FORCE="${FORCE:-false}"
REPLACE_PREVIOUS="${REPLACE_PREVIOUS:-true}"

set -- publish-daily-discord \
  --date "$RUN_DATE" \
  --config "$CONFIG_PATH"

if bool_flag "$DRY_RUN"; then
  set -- "$@" --dry-run
fi

if bool_flag "$PRINT_ONLY"; then
  set -- "$@" --print-only
fi

if bool_flag "$FORCE"; then
  set -- "$@" --force
fi

if bool_flag "$REPLACE_PREVIOUS"; then
  set -- "$@" --replace-previous
else
  set -- "$@" --no-replace-previous
fi

"$CLI_BIN" "$@"
