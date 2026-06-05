#!/usr/bin/env python
"""Publish persisted World Cup combo tickets through the controlled service.

Dry-run by default. Use --execute to send Discord messages and mark tickets.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select

from football_predictor.cli import _load_discord_routing
from football_predictor.config.settings import get_settings
from football_predictor.db import models as db_models
from football_predictor.db.session import create_db_engine, create_session_factory, session_scope
from football_predictor.discord.service import DiscordDeliveryService
from football_predictor.world_cup_combos.config import load_world_cup_combo_config
from football_predictor.world_cup_combos.enums import ComboTicketStatus
from football_predictor.world_cup_combos.worldcup_combo_lock_service import (
    combo_ticket_candidate_from_payload,
)
from football_predictor.world_cup_combos.worldcup_combo_publication_service import (
    WorldCupComboPublicationService,
)

PUBLISHABLE_STATUSES = {
    ComboTicketStatus.DRAFT.value,
    ComboTicketStatus.WATCHLIST_STAFF.value,
    ComboTicketStatus.PRE_LOCK_REVALIDATION.value,
    ComboTicketStatus.LOCKED.value,
    ComboTicketStatus.STAFF_ONLY.value,
    ComboTicketStatus.NO_BET.value,
}


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    config_path = args.config or settings.world_cup_combos_config_path
    config = load_world_cup_combo_config(config_path)
    if not config.enabled:
        print(json.dumps({"enabled": False, "message": "worldcup_combos disabled"}, indent=2))
        return

    target_date = date.fromisoformat(args.date) if args.date else None
    _, channels, webhooks = _load_discord_routing(settings)
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        delivery = DiscordDeliveryService(
            session,
            channels_config=channels,
            webhooks_config=webhooks,
            legacy_webhook_url=settings.discord_webhook_url,
            timeout=settings.discord_timeout_seconds,
        )
        service = WorldCupComboPublicationService(
            session,
            config,
            delivery_service=delivery,
        )
        results = []
        for record in _load_records(session, config.competition_key, target_date):
            ticket = combo_ticket_candidate_from_payload(record.payload_json)
            results.append(
                _publish_record(
                    service,
                    record,
                    ticket,
                    execute=args.execute,
                    now=datetime.now(tz=UTC),
                ).__dict__
            )
    print(
        json.dumps(
            {
                "enabled": True,
                "execute": args.execute,
                "target_date": target_date.isoformat() if target_date else None,
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_records(session, competition_key: str, target_date: date | None):
    stmt = (
        select(db_models.ComboTicket)
        .where(db_models.ComboTicket.competition_key == competition_key)
        .where(db_models.ComboTicket.status.in_(PUBLISHABLE_STATUSES))
        .order_by(db_models.ComboTicket.combo_date.asc(), db_models.ComboTicket.id.asc())
    )
    if target_date is not None:
        stmt = stmt.where(db_models.ComboTicket.combo_date == target_date)
    return session.execute(stmt).scalars()


def _publish_record(
    service: WorldCupComboPublicationService,
    record: db_models.ComboTicket,
    ticket,
    *,
    execute: bool,
    now: datetime,
):
    dry_run = not execute
    if record.status == ComboTicketStatus.LOCKED.value:
        return service.publish_locked(
            ticket,
            locked_at=now,
            dry_run=dry_run,
            execute=execute,
        )
    if record.status == ComboTicketStatus.NO_BET.value:
        return service.publish_no_bet(
            reason=ticket.no_publish_reason or "no_bet",
            ticket=ticket,
            dry_run=dry_run,
            execute=execute,
        )
    return service.publish_watchlist_staff(
        ticket,
        dry_run=dry_run,
        execute=execute,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--date", default=None, help="Optional combo_date in YYYY-MM-DD.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Send Discord messages and mark tickets. Defaults to dry-run.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
