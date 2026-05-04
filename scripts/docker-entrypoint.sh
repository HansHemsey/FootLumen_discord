#!/bin/sh
set -eu

mkdir -p /app/data/raw /app/data/processed /app/data/models

if [ "$#" -eq 0 ]; then
  set -- doctor
fi

case "$1" in
  football-predictor|python|python3|alembic|bash|sh)
    exec "$@"
    ;;
  *)
    exec football-predictor "$@"
    ;;
esac
