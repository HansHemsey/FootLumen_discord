#!/usr/bin/env python
"""Settle World Cup combo tickets after fixture results.

Dry-run by default. Use --execute to write settlement payloads and snapshots.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from football_predictor.config.settings import get_settings
from football_predictor.db.session import create_db_engine, create_session_factory, session_scope
from football_predictor.world_cup_combos.config import load_world_cup_combo_config
from football_predictor.world_cup_combos.worldcup_combo_settlement import (
    WorldCupComboSettlementService,
)


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    config_path = args.config or settings.world_cup_combos_config_path
    config = load_world_cup_combo_config(config_path)
    if not config.enabled:
        print(json.dumps({"enabled": False, "message": "worldcup_combos disabled"}, indent=2))
        return

    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        service = WorldCupComboSettlementService(session)
        results = service.settle_open_records(
            settled_at=datetime.now(tz=UTC),
            execute=args.execute,
        )
    print(
        json.dumps(
            {
                "enabled": True,
                "execute": args.execute,
                "results": [result.__dict__ for result in results],
            },
            indent=2,
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write settlement payloads and snapshots. Defaults to dry-run.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
