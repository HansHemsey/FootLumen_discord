#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'USAGE'
Usage: scripts/smoke_test_live.sh [--date YYYY-MM-DD] [--fixture FIXTURE_ID] [--league LEAGUE_ID] [--season SEASON] [--window early|mid|late|now]

Live smoke requires API_FOOTBALL_KEY.
Discord is not sent unless SEND_DISCORD=true is set explicitly.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --date)
      SMOKE_DATE="${2:?Missing value for --date}"
      shift
      ;;
    --fixture)
      SMOKE_FIXTURE_ID="${2:?Missing value for --fixture}"
      shift
      ;;
    --league)
      SMOKE_LEAGUE_ID="${2:?Missing value for --league}"
      shift
      ;;
    --season)
      SMOKE_SEASON="${2:?Missing value for --season}"
      shift
      ;;
    --window)
      SMOKE_WINDOW="${2:?Missing value for --window}"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [ -z "${API_FOOTBALL_KEY:-}" ]; then
  echo "API_FOOTBALL_KEY is required for live smoke." >&2
  exit 1
fi

export SMOKE_LIVE=true
export SMOKE_DATE="${SMOKE_DATE:-$(date +%F)}"
export SMOKE_WINDOW="${SMOKE_WINDOW:-now}"
export SMOKE_SEND_DISCORD="${SEND_DISCORD:-false}"
export SMOKE_PRINT_ONLY="${PRINT_ONLY:-false}"
export SMOKE_DATABASE_URL="${SMOKE_DATABASE_URL:-sqlite:///./data/smoke/football_predictor_smoke_live.db}"

if [ -n "${SMOKE_FIXTURE_ID:-}" ]; then
  echo "Live smoke will refresh fixture=$SMOKE_FIXTURE_ID"
elif [ -n "${SMOKE_LEAGUE_ID:-}" ]; then
  echo "Live smoke will refresh date=$SMOKE_DATE league=$SMOKE_LEAGUE_ID season=${SMOKE_SEASON:-any}"
else
  echo "Live smoke will refresh date=$SMOKE_DATE for configured competitions."
fi

scripts/smoke_test.sh --live
