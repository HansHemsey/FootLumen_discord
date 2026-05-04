#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"
CLI_BIN="$(resolve_cli_bin)"
RUN_DATE="${DATE:-$(default_run_date)}"
CONFIG_PATH="${CONFIG:-config/competitions.yaml}"
REFRESH_DATA="${REFRESH_DATA:-true}"
SEND_DISCORD="${SEND_DISCORD:-false}"
DRY_RUN="${DRY_RUN:-true}"
PRINT_ONLY="${PRINT_ONLY:-false}"
FORCE="${FORCE:-false}"
REPLACE_PREVIOUS="${REPLACE_PREVIOUS:-true}"
SAVE_RAW="${SAVE_RAW:-true}"
PUBLISH_DISCORD="${PUBLISH_DISCORD:-true}"

run_optional() {
  label="$1"
  shift
  echo "$label"
  if ! "$@"; then
    echo "Warning: $label failed; continuing daily automation." >&2
  fi
}

mkdir -p data/raw data/processed data/models

"$CLI_BIN" doctor --strict
"$CLI_BIN" init-db
"$CLI_BIN" seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json

if bool_flag "$REFRESH_DATA"; then
  enabled_competitions "$CONFIG_PATH" | while IFS="$(printf '\t')" read -r league_id season competition_key; do
    [ -n "$league_id" ] || continue
    standings_cmd="ingest-standings --league $league_id --season $season --refresh-api"
    odds_cmd="ingest-odds --date $RUN_DATE --league $league_id --season $season --refresh-api"
    if bool_flag "$SAVE_RAW"; then
      standings_cmd="$standings_cmd --save-raw"
      odds_cmd="$odds_cmd --save-raw"
    fi
    # shellcheck disable=SC2086
    run_optional "Refreshing standings competition=$competition_key league=$league_id season=$season" "$CLI_BIN" $standings_cmd
    # shellcheck disable=SC2086
    run_optional "Refreshing odds date=$RUN_DATE competition=$competition_key league=$league_id season=$season" "$CLI_BIN" $odds_cmd
  done
fi

if bool_flag "$PUBLISH_DISCORD"; then
  PUBLISH_DRY_RUN="$DRY_RUN"
  if ! bool_flag "$SEND_DISCORD"; then
    PUBLISH_DRY_RUN="true"
  fi
  DATE="$RUN_DATE" \
    CONFIG="$CONFIG_PATH" \
    DRY_RUN="$PUBLISH_DRY_RUN" \
    PRINT_ONLY="$PRINT_ONLY" \
    FORCE="$FORCE" \
    REPLACE_PREVIOUS="$REPLACE_PREVIOUS" \
    scripts/publish_daily_discord.sh
  DATE="$RUN_DATE" \
    DRY_RUN="$PUBLISH_DRY_RUN" \
    PRINT_ONLY="$PRINT_ONLY" \
    FORCE="$FORCE" \
    INCLUDE_PREVIOUS_WEEK_FINALIZATION="${INCLUDE_PREVIOUS_WEEK_FINALIZATION:-true}" \
    REPLACE_CURRENT_WEEK="${REPLACE_CURRENT_WEEK:-true}" \
    scripts/publish_weekly_score.sh
fi
echo "Daily morning refresh complete for date=$RUN_DATE"
