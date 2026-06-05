#!/usr/bin/env python
"""Dry-run World Cup combo publication decisions without Discord publish."""

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
from football_predictor.world_cup_combos.worldcup_combo_lock_service import (
    WorldCupComboLockService,
)
from football_predictor.world_cup_combos.worldcup_combo_publication_service import (
    WorldCupComboPublicationService,
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
            .order_by(db_models.ComboTicket.combo_date.asc(), db_models.ComboTicket.id.asc())
        ).scalars()
        lock_service = WorldCupComboLockService(config)
        publication_service = WorldCupComboPublicationService(session, config)
        results = []
        for record in records:
            ticket = lock_service.lock_persisted_ticket(
                session,
                record,
                now=now,
                execute=False,
            )
            if ticket.publication_decision.value == "LOCKED":
                result = publication_service.publish_locked(
                    ticket,
                    locked_at=now,
                    dry_run=True,
                    execute=False,
                )
            elif ticket.publication_decision.value == "NO_BET":
                result = publication_service.publish_no_bet(
                    reason=ticket.no_publish_reason or "no_bet",
                    ticket=ticket,
                    dry_run=True,
                    execute=False,
                )
            else:
                result = publication_service.publish_watchlist_staff(
                    ticket,
                    dry_run=True,
                    execute=False,
                )
            results.append(result.__dict__)
    print(json.dumps({"enabled": True, "dry_run": True, "results": results}, indent=2))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    main()
