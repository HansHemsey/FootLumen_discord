#!/usr/bin/env python
"""Inspect and optionally compact World Cup combo snapshots.

Dry-run by default. Use --execute to delete probable duplicate non-critical snapshots.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from football_predictor.config.settings import get_settings
from football_predictor.db.session import create_db_engine, create_session_factory, session_scope
from football_predictor.world_cup_combos.snapshot_maintenance import analyze_combo_snapshots


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        summary = analyze_combo_snapshots(session, execute=args.execute)
    print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="Reserved for cron symmetry.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Delete probable duplicate non-critical snapshots. Defaults to dry-run.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
