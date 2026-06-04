#!/usr/bin/env python
"""Generate World Cup combo tickets.

Dry-run by default. Use --execute to persist combo_tickets and snapshots.
No Discord message is published by this command.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from football_predictor.config.settings import get_settings
from football_predictor.db.session import create_db_engine, create_session_factory, session_scope
from football_predictor.world_cup_combos.config import load_world_cup_combo_config
from football_predictor.world_cup_combos.persistence import ensure_combo_tables
from football_predictor.world_cup_combos.worldcup_combo_run_service import (
    WorldCupComboRunService,
)


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    config_path = args.config or settings.world_cup_combos_config_path
    config = load_world_cup_combo_config(config_path)
    target_date = date.fromisoformat(args.date) if args.date else None

    engine = create_db_engine(settings.database_url)
    if args.execute:
        ensure_combo_tables(engine)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        summary = WorldCupComboRunService(session, config).run(
            target_date=target_date,
            execute=args.execute,
        )
    print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to worldcup_combos.yaml. Defaults to settings.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Optional Paris date filter in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Persist generated tickets and snapshots. Defaults to dry-run.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
