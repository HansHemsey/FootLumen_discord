#!/usr/bin/env python
"""Revalidate and lock persisted World Cup combo tickets.

Dry-run by default. Use --execute to write status changes and pre_lock snapshots.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from football_predictor.config.settings import get_settings
from football_predictor.db import models as db_models
from football_predictor.db.session import create_db_engine, create_session_factory, session_scope
from football_predictor.world_cup_combos.config import load_world_cup_combo_config
from football_predictor.world_cup_combos.enums import ComboTicketStatus
from football_predictor.world_cup_combos.worldcup_combo_lock_service import (
    WorldCupComboLockService,
)


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    config_path = args.config or settings.world_cup_combos_config_path
    config = load_world_cup_combo_config(config_path)
    if not config.enabled:
        print(json.dumps({"enabled": False, "message": "worldcup_combos disabled"}, indent=2))
        return

    now = datetime.now(tz=UTC)
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        records = session.execute(
            select(db_models.ComboTicket)
            .where(db_models.ComboTicket.competition_key == config.competition_key)
            .where(
                db_models.ComboTicket.status.notin_(
                    (
                        ComboTicketStatus.LOCKED.value,
                        ComboTicketStatus.SETTLED.value,
                    )
                )
            )
            .order_by(db_models.ComboTicket.combo_date.asc(), db_models.ComboTicket.id.asc())
        ).scalars()
        service = WorldCupComboLockService(config)
        results = [
            {
                "ticket_key": record.ticket_key,
                "before": record.status,
                "after": service.lock_persisted_ticket(
                    session,
                    record,
                    now=now,
                    execute=args.execute,
                ).publication_decision.value,
            }
            for record in records
        ]
    print(
        json.dumps(
            {"enabled": True, "execute": args.execute, "results": results},
            indent=2,
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write status changes and pre-lock snapshots. Defaults to dry-run.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
