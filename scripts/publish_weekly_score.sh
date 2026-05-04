#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"
CLI_BIN="$(resolve_cli_bin)"
RUN_DATE="${DATE:-$(default_run_date)}"
DRY_RUN="${DRY_RUN:-true}"
PRINT_ONLY="${PRINT_ONLY:-false}"
FORCE="${FORCE:-false}"
INCLUDE_PREVIOUS_WEEK_FINALIZATION="${INCLUDE_PREVIOUS_WEEK_FINALIZATION:-true}"
REPLACE_CURRENT_WEEK="${REPLACE_CURRENT_WEEK:-true}"

set -- publish-weekly-score --date "$RUN_DATE"

if bool_flag "$DRY_RUN"; then
  set -- "$@" --dry-run
fi

if bool_flag "$PRINT_ONLY"; then
  set -- "$@" --print-only
fi

if bool_flag "$FORCE"; then
  set -- "$@" --force
fi

if bool_flag "$INCLUDE_PREVIOUS_WEEK_FINALIZATION"; then
  set -- "$@" --include-previous-week-finalization
else
  set -- "$@" --no-include-previous-week-finalization
fi

if bool_flag "$REPLACE_CURRENT_WEEK"; then
  set -- "$@" --replace-current-week
else
  set -- "$@" --no-replace-current-week
fi

"$CLI_BIN" "$@"
