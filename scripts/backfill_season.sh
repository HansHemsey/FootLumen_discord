#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

. "$ROOT_DIR/scripts/lib.sh"

PYTHON_BIN="$(resolve_python_bin)"

SEASON="${SEASON:-${BACKFILL_SEASON:-}}"
if [ -z "$SEASON" ]; then
  echo "Missing SEASON. Example: SEASON=2024 scripts/backfill_season.sh" >&2
  exit 2
fi

case "$SEASON" in
  *[!0-9]*|"")
    echo "Invalid SEASON='$SEASON'. Use an API-Football season year like 2024." >&2
    exit 2
    ;;
esac

CONFIG_SOURCE="${CONFIG:-}"
if [ -z "$CONFIG_SOURCE" ]; then
  if [ -f "config/competitions_history.yaml" ]; then
    CONFIG_SOURCE="config/competitions_history.yaml"
  else
    CONFIG_SOURCE="config/competitions.yaml"
  fi
fi
BACKFILL_DIR="${BACKFILL_DIR:-data/processed/backfill}"
BACKFILL_CONFIG="${BACKFILL_CONFIG:-$BACKFILL_DIR/competitions_${SEASON}.yaml}"
BACKFILL_INCLUDE_CUPS="${BACKFILL_INCLUDE_CUPS:-false}"

DETAILS_FROM="${DETAILS_FROM:-${SEASON}-08-01}"
DETAILS_TO="${DETAILS_TO:-$("$PYTHON_BIN" - "$SEASON" <<'PY'
import sys

season = int(sys.argv[1])
print(f"{season + 1}-07-31")
PY
)}"

mkdir -p "$BACKFILL_DIR"

"$PYTHON_BIN" - "$CONFIG_SOURCE" "$BACKFILL_CONFIG" "$SEASON" "$BACKFILL_INCLUDE_CUPS" <<'PY'
from pathlib import Path
import sys

import yaml

source = Path(sys.argv[1])
target = Path(sys.argv[2])
season = int(sys.argv[3])
include_cups = sys.argv[4].lower() == "true"

payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
competitions = payload.get("competitions")
if not isinstance(competitions, list):
    raise SystemExit(f"Invalid competitions config: {source}")

def looks_like_cup(competition: dict) -> bool:
    key = str(competition.get("key") or "").lower()
    ref_key = str(competition.get("reference_key") or "").lower()
    name = str(competition.get("name") or "").lower()
    country = str(competition.get("country") or "").lower()
    return "cup" in key or "cup" in ref_key or "cup" in name or country == "world"


def normalized_history_row(competition: dict, target_season: int) -> dict:
    row = dict(competition)
    reference_key = row.get("reference_key") or row.get("key")
    if reference_key:
        row["reference_key"] = str(reference_key)
        row["key"] = f"{reference_key}_{target_season}"
    row["season"] = target_season
    row["enabled"] = True
    return row


selected: list[dict] = []
fallback_base: list[dict] = []
for competition in competitions:
    if not isinstance(competition, dict):
        continue
    if looks_like_cup(competition) and not include_cups:
        continue
    if not competition.get("enabled", True):
        continue
    if int(competition.get("season") or 0) == season:
        selected.append(dict(competition))
    fallback_base.append(dict(competition))

if not selected:
    selected = [normalized_history_row(competition, season) for competition in fallback_base]

if not selected:
    raise SystemExit(f"No enabled competitions available for season={season} in {source}")

target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(
    yaml.safe_dump({"competitions": selected}, sort_keys=False, allow_unicode=True),
    encoding="utf-8",
)
PY

echo "Backfill season=$SEASON from=$DETAILS_FROM to=$DETAILS_TO source=$CONFIG_SOURCE config=$BACKFILL_CONFIG include_cups=$BACKFILL_INCLUDE_CUPS"
echo "Details: only='${DETAILS_ONLY:-statistics events players}' statuses='${DETAILS_STATUSES:-FT AET PEN}' limit='${DETAILS_LIMIT:-400}' delay='${DETAILS_DELAY_SECONDS:-3}'"

CONFIG="$BACKFILL_CONFIG" \
REFRESH_TEAMS="${REFRESH_TEAMS:-true}" \
REFRESH_FIXTURES="${REFRESH_FIXTURES:-true}" \
REFRESH_STANDINGS="${REFRESH_STANDINGS:-true}" \
REFRESH_ODDS="${REFRESH_ODDS:-false}" \
REFRESH_DETAILS="${REFRESH_DETAILS:-true}" \
SAVE_RAW="${SAVE_RAW:-true}" \
DETAILS_FROM="$DETAILS_FROM" \
DETAILS_TO="$DETAILS_TO" \
DETAILS_STATUSES="${DETAILS_STATUSES:-FT AET PEN}" \
DETAILS_LIMIT="${DETAILS_LIMIT:-400}" \
DETAILS_DELAY_SECONDS="${DETAILS_DELAY_SECONDS:-2}" \
DETAILS_ONLY="${DETAILS_ONLY:-statistics events players}" \
DETAILS_SKIP_IF_COMPLETE="${DETAILS_SKIP_IF_COMPLETE:-true}" \
RESOLVE_UNKNOWN_PLAYERS="${RESOLVE_UNKNOWN_PLAYERS:-false}" \
UNKNOWN_PLAYERS_LIMIT="${UNKNOWN_PLAYERS_LIMIT:-50}" \
UNKNOWN_PLAYERS_DELAY_SECONDS="${UNKNOWN_PLAYERS_DELAY_SECONDS:-2}" \
scripts/refresh_all_leagues.sh
