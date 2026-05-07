#!/bin/sh

resolve_project_root() {
  CDPATH= cd -- "$(dirname -- "$0")/.." && pwd
}

resolve_cli_bin() {
  if [ -n "${FOOTBALL_PREDICTOR_BIN:-}" ]; then
    printf '%s\n' "$FOOTBALL_PREDICTOR_BIN"
    return
  fi
  if [ -x "$ROOT_DIR/scripts/football_predictor_cli.sh" ]; then
    printf '%s\n' "$ROOT_DIR/scripts/football_predictor_cli.sh"
    return
  fi
  if [ -x "$ROOT_DIR/.venv/bin/football-predictor" ]; then
    printf '%s\n' "$ROOT_DIR/.venv/bin/football-predictor"
    return
  fi
  printf '%s\n' "football-predictor"
}

resolve_python_bin() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    printf '%s\n' "$PYTHON_BIN"
    return
  fi
  if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
    printf '%s\n' "$ROOT_DIR/.venv/bin/python"
    return
  fi
  printf '%s\n' "python3"
}

default_run_date() {
  "$PYTHON_BIN" - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo
import os

timezone_name = os.getenv("APP_TIMEZONE", "Europe/Paris")
print(datetime.now(ZoneInfo(timezone_name)).date().isoformat())
PY
}

enabled_competitions() {
  config_path="${1:-config/competitions.yaml}"
  "$PYTHON_BIN" - "$config_path" <<'PY'
from pathlib import Path
import sys
import yaml

config_path = Path(sys.argv[1])
data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
for competition in data.get("competitions", []):
    if not competition.get("enabled", True):
        continue
    league_id = competition.get("league_id")
    season = competition.get("season")
    key = competition.get("key") or ""
    if league_id is None or season is None:
        continue
    print(f"{league_id}\t{season}\t{key}")
PY
}

dataset_args_for_flags() {
  config_path="${1:-config/competitions.yaml}"
  league_flag="${2:---league}"
  season_flag="${3:---season}"
  "$PYTHON_BIN" - "$config_path" "$league_flag" "$season_flag" <<'PY'
from pathlib import Path
import sys
import yaml

config_path = Path(sys.argv[1])
league_flag = sys.argv[2]
season_flag = sys.argv[3]
data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
league_ids: list[int] = []
seasons: list[int] = []
for competition in data.get("competitions", []):
    if not competition.get("enabled", True):
        continue
    league_id = competition.get("league_id")
    season = competition.get("season")
    if league_id is None or season is None:
        continue
    if league_id not in league_ids:
        league_ids.append(league_id)
    if season not in seasons:
        seasons.append(season)
for league_id in league_ids:
    print(f"{league_flag} {league_id}")
for season in seasons:
    print(f"{season_flag} {season}")
PY
}

competition_dataset_args() {
  dataset_args_for_flags "${1:-config/competitions.yaml}" "--league" "--season"
}

competition_dataset_args_ou() {
  dataset_args_for_flags "${1:-config/competitions.yaml}" "--league-id" "--season"
}

bool_flag() {
  [ "${1:-false}" = "true" ]
}
