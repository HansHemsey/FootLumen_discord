#!/usr/bin/env python
"""Dry-run World Cup combo ticket builder without Discord publish or DB writes."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from football_predictor.config.settings import get_settings
from football_predictor.db.session import create_db_engine, create_session_factory, session_scope
from football_predictor.world_cup_combos.config import load_world_cup_combo_config
from football_predictor.world_cup_combos.worldcup_combo_builder import WorldCupComboBuilder
from football_predictor.world_cup_combos.worldcup_combo_leg_selector import (
    WorldCupComboLegSelector,
)
from football_predictor.world_cup_combos.worldcup_combo_sessions import (
    WorldCupComboSessionService,
)


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    config_path = args.config or settings.world_cup_combos_config_path
    config = load_world_cup_combo_config(config_path)
    target_date = date.fromisoformat(args.date) if args.date else None

    if not config.enabled:
        print(
            json.dumps(
                {
                    "enabled": False,
                    "config_path": str(config_path),
                    "sessions": 0,
                    "tickets": 0,
                    "message": "worldcup_combos disabled; builder dry-run is a no-op",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as db_session:
        session_service = WorldCupComboSessionService(db_session, config)
        sessions = session_service.build_sessions(target_date=target_date)
        selection = WorldCupComboLegSelector(db_session, config).select_candidates(sessions)
        candidates_by_session = defaultdict(list)
        for candidate in selection.candidates:
            for combo_session in selection.sessions:
                session_fixture_ids = {
                    fixture.fixture_id for fixture in combo_session.fixtures
                }
                if candidate.fixture_id in session_fixture_ids:
                    candidates_by_session[combo_session.session_key].append(candidate)
                    break
        builder = WorldCupComboBuilder(config)
        tickets_by_session = {
            combo_session.session_key: builder.build_for_session(
                combo_session,
                candidates_by_session.get(combo_session.session_key, []),
            )
            for combo_session in selection.sessions
        }

    tickets = [ticket for tickets in tickets_by_session.values() for ticket in tickets]
    summary = {
        "enabled": True,
        "config_path": str(config_path),
        "target_date": target_date.isoformat() if target_date else None,
        "sessions": len(sessions),
        "candidate_legs": len(selection.candidates),
        "tickets": len(tickets),
        "session_summaries": [
            {
                "session_key": combo_session.session_key,
                "fixtures": len(combo_session.fixtures),
                "candidate_legs": len(candidates_by_session.get(combo_session.session_key, [])),
                "tickets": [
                    {
                        "ticket_key": ticket.ticket_key,
                        "legs_count": ticket.legs_count,
                        "combined_decimal_odds": ticket.combined_decimal_odds,
                        "combined_ev_adjusted": ticket.combined_ev_adjusted,
                        "combined_confidence_score": ticket.combined_confidence_score,
                        "combined_confidence_label": ticket.combined_confidence_label,
                        "publication_decision": ticket.publication_decision.value,
                        "no_publish_reason": ticket.no_publish_reason,
                        "post_lock_risk_score": ticket.post_lock_risk_score,
                        "warnings": ticket.warnings,
                    }
                    for ticket in tickets_by_session.get(combo_session.session_key, [])
                ],
            }
            for combo_session in sessions
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


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
    return parser.parse_args()


if __name__ == "__main__":
    main()
