#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"
CLI_BIN="$(resolve_cli_bin)"
CONFIG_PATH="${CONFIG:-config/competitions.yaml}"
REFRESH_TEAMS="${REFRESH_TEAMS:-false}"
REFRESH_FIXTURES="${REFRESH_FIXTURES:-true}"
REFRESH_STANDINGS="${REFRESH_STANDINGS:-true}"
REFRESH_ODDS="${REFRESH_ODDS:-true}"
REFRESH_DETAILS="${REFRESH_DETAILS:-false}"
SAVE_RAW="${SAVE_RAW:-true}"
DETAILS_STATUS="${DETAILS_STATUS:-FT}"
DETAILS_STATUSES="${DETAILS_STATUSES:-$DETAILS_STATUS}"
DETAILS_DAYS_BACK="${DETAILS_DAYS_BACK:-}"
DETAILS_FROM="${DETAILS_FROM:-}"
DETAILS_TO="${DETAILS_TO:-}"
DETAILS_LIMIT="${DETAILS_LIMIT:-5}"
DETAILS_DELAY_SECONDS="${DETAILS_DELAY_SECONDS:-2}"
DETAILS_ONLY="${DETAILS_ONLY:-statistics events players}"
DETAILS_INCLUDE_UPCOMING="${DETAILS_INCLUDE_UPCOMING:-false}"
DETAILS_SKIP_IF_COMPLETE="${DETAILS_SKIP_IF_COMPLETE:-true}"
RESOLVE_UNKNOWN_PLAYERS="${RESOLVE_UNKNOWN_PLAYERS:-false}"
UNKNOWN_PLAYERS_INPUT="${UNKNOWN_PLAYERS_INPUT:-data/processed/unknown_players.jsonl}"
UNKNOWN_PLAYERS_LIMIT="${UNKNOWN_PLAYERS_LIMIT:-50}"
UNKNOWN_PLAYERS_DELAY_SECONDS="${UNKNOWN_PLAYERS_DELAY_SECONDS:-2}"
UNKNOWN_PLAYERS_SQUADS_FALLBACK="${UNKNOWN_PLAYERS_SQUADS_FALLBACK:-true}"

run_optional() {
  label="$1"
  shift
  echo "$label"
  if ! "$@"; then
    echo "Warning: $label failed; continuing refresh." >&2
  fi
}

"$CLI_BIN" doctor --strict
"$CLI_BIN" init-db
"$CLI_BIN" seed-reference-from-docs \
  --reference docs/api_football_reference.json \
  --players docs/api_football_players_reference.json

if bool_flag "$REFRESH_TEAMS"; then
  run_optional "Refreshing teams config=$CONFIG_PATH" \
    "$CLI_BIN" ingest-teams --config "$CONFIG_PATH" --refresh-api
fi

enabled_competitions "$CONFIG_PATH" | while IFS="$(printf '\t')" read -r league_id season competition_key; do
  [ -n "$league_id" ] || continue

  save_raw_flag=""
  if bool_flag "$SAVE_RAW"; then
    save_raw_flag="--save-raw"
  fi

  if bool_flag "$REFRESH_FIXTURES"; then
    # shellcheck disable=SC2086
    run_optional "Refreshing fixtures competition=$competition_key league=$league_id season=$season" \
      "$CLI_BIN" ingest-fixtures --league "$league_id" --season "$season" --refresh-api $save_raw_flag
  fi

  if bool_flag "$REFRESH_STANDINGS"; then
    # shellcheck disable=SC2086
    run_optional "Refreshing standings competition=$competition_key league=$league_id season=$season" \
      "$CLI_BIN" ingest-standings --league "$league_id" --season "$season" --refresh-api $save_raw_flag
  fi

  if bool_flag "$REFRESH_ODDS"; then
    # shellcheck disable=SC2086
    run_optional "Refreshing odds competition=$competition_key league=$league_id season=$season" \
      "$CLI_BIN" ingest-odds --league "$league_id" --season "$season" --refresh-api $save_raw_flag
  fi

  if bool_flag "$REFRESH_DETAILS"; then
    set -- ingest-fixture-details \
      --league "$league_id" \
      --season "$season" \
      --refresh-api \
      --delay-seconds "$DETAILS_DELAY_SECONDS" \
      --stop-on-rate-limit
    if [ -n "$DETAILS_DAYS_BACK" ]; then
      set -- "$@" --days-back "$DETAILS_DAYS_BACK"
    else
      if [ -n "$DETAILS_FROM" ]; then
        set -- "$@" --from-date "$DETAILS_FROM"
      fi
      if [ -n "$DETAILS_TO" ]; then
        set -- "$@" --to-date "$DETAILS_TO"
      fi
    fi
    if bool_flag "$DETAILS_INCLUDE_UPCOMING"; then
      set -- "$@" --include-upcoming
    elif [ -n "$DETAILS_STATUSES" ]; then
      for status_key in $DETAILS_STATUSES; do
        set -- "$@" --status "$status_key"
      done
    fi
    if bool_flag "$SAVE_RAW"; then
      set -- "$@" --save-raw
    fi
    if bool_flag "$DETAILS_SKIP_IF_COMPLETE"; then
      set -- "$@" --skip-if-complete
    fi
    for detail_key in $DETAILS_ONLY; do
      set -- "$@" --only "$detail_key"
    done
    if [ -n "${LIMIT:-$DETAILS_LIMIT}" ]; then
      set -- "$@" --limit "${LIMIT:-$DETAILS_LIMIT}"
    fi
    run_optional "Refreshing fixture details competition=$competition_key league=$league_id season=$season" \
      "$CLI_BIN" "$@"
  fi
done

if bool_flag "$RESOLVE_UNKNOWN_PLAYERS"; then
  set -- resolve-unknown-players \
    --refresh-api \
    --input "$UNKNOWN_PLAYERS_INPUT" \
    --limit "$UNKNOWN_PLAYERS_LIMIT" \
    --delay-seconds "$UNKNOWN_PLAYERS_DELAY_SECONDS"
  if bool_flag "$SAVE_RAW"; then
    set -- "$@" --save-raw
  fi
  if ! bool_flag "$UNKNOWN_PLAYERS_SQUADS_FALLBACK"; then
    set -- "$@" --no-squads-fallback
  fi
  run_optional "Resolving unknown live players input=$UNKNOWN_PLAYERS_INPUT limit=$UNKNOWN_PLAYERS_LIMIT" \
    "$CLI_BIN" "$@"
fi
