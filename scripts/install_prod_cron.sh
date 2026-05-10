#!/bin/sh
# Install the production crontab for autonomous Discord publication.
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

CRONTAB_FILE="${CRONTAB_FILE:-config/prod.crontab}"
BACKUP_DIR="${CRON_BACKUP_DIR:-logs/cron}"

if [ ! -f "$CRONTAB_FILE" ]; then
  echo "Missing crontab file: $CRONTAB_FILE" >&2
  exit 2
fi

mkdir -p "$BACKUP_DIR"
BACKUP_PATH="$BACKUP_DIR/crontab.backup.$(date +%Y%m%d_%H%M%S)"
if crontab -l > "$BACKUP_PATH" 2>/dev/null; then
  echo "Current crontab backed up to $BACKUP_PATH"
else
  rm -f "$BACKUP_PATH"
  echo "No existing crontab to back up."
fi

crontab "$CRONTAB_FILE"
echo "Installed production crontab from $CRONTAB_FILE"
echo "Verify with: crontab -l"
