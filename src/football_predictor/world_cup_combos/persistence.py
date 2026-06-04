"""Persistence helpers for World Cup combo tickets.

Sprint 1 keeps this module deliberately small: it creates the combo tables
idempotently and can persist domain snapshots, but it does not build, publish,
or settle combo tickets.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from football_predictor.db import models as db_models
from football_predictor.db.repositories import upsert_by_fields
from football_predictor.world_cup_combos.models import (
    ComboLegSnapshot,
    ComboTicketCandidate,
    ComboTicketSnapshot,
)

COMBO_TABLES = (
    db_models.ComboTicket.__table__,
    db_models.ComboTicketLeg.__table__,
    db_models.ComboTicketSnapshot.__table__,
)


def ensure_combo_tables(engine: Engine) -> None:
    db_models.Base.metadata.create_all(engine, tables=COMBO_TABLES)


def persist_combo_ticket_candidate(
    session: Session,
    ticket: ComboTicketCandidate,
    *,
    model_versions_json: dict | None = None,
) -> db_models.ComboTicket:
    record = upsert_by_fields(
        session,
        db_models.ComboTicket,
        {"ticket_key": ticket.ticket_key},
        {
            "status": ticket.publication_decision.value,
            "competition_key": ticket.competition_key,
            "league_id": ticket.league_id,
            "season": ticket.season,
            "combo_date": ticket.combo_date,
            "session_key": ticket.session_key,
            "first_kickoff_at": ticket.first_kickoff_at,
            "last_kickoff_at": ticket.last_kickoff_at,
            "lock_time": ticket.lock_time,
            "legs_count": ticket.legs_count,
            "combined_decimal_odds": ticket.combined_decimal_odds,
            "combined_probability_raw": ticket.combined_probability_raw,
            "combined_probability_adjusted": ticket.combined_probability_adjusted,
            "combined_fair_odds": ticket.combined_fair_odds,
            "combined_ev_raw": ticket.combined_ev_raw,
            "combined_ev_adjusted": ticket.combined_ev_adjusted,
            "combined_confidence_score": ticket.combined_confidence_score,
            "combined_confidence_label": ticket.combined_confidence_label,
            "post_lock_risk_score": ticket.post_lock_risk_score,
            "freshness_score": ticket.freshness_score,
            "lineup_risk_score": ticket.lineup_risk_score,
            "publication_decision": ticket.publication_decision.value,
            "no_publish_reason": ticket.no_publish_reason,
            "model_versions_json": model_versions_json or {},
            "warnings_json": ticket.warnings,
            "payload_json": ticket.to_json_dict(),
        },
    )
    session.flush()
    for leg_order, leg in enumerate(ticket.legs, start=1):
        upsert_by_fields(
            session,
            db_models.ComboTicketLeg,
            {"ticket_id": record.id, "leg_order": leg_order},
            {
                "fixture_id": leg.fixture_id,
                "kickoff_at_utc": leg.kickoff_at_utc,
                "market_type": leg.market_type.value,
                "market_scope": leg.market_scope.value,
                "selection": leg.selection,
                "decimal_odd": leg.decimal_odd,
                "model_probability": leg.model_probability,
                "market_probability": leg.market_probability,
                "edge": leg.edge,
                "ev": leg.ev,
                "confidence_score": leg.confidence_score,
                "confidence_label": leg.confidence_label,
                "data_quality_score": leg.data_quality_score,
                "odds_snapshot_id": leg.odds_snapshot_id,
                "prediction_snapshot_id": leg.prediction_snapshot_id,
                "lineup_status": leg.lineup_status,
                "odds_last_update": leg.odds_last_update,
                "prediction_generated_at": leg.prediction_generated_at,
                "model_versions_json": model_versions_json or {},
                "warnings_json": leg.warnings,
                "payload_json": leg.to_json_dict(),
            },
        )
    return record


def persist_combo_ticket_snapshot(
    session: Session,
    snapshot: ComboTicketSnapshot,
    *,
    ticket_id: int | None = None,
) -> db_models.ComboTicketSnapshot:
    record = db_models.ComboTicketSnapshot(
        ticket_id=ticket_id,
        ticket_key=snapshot.ticket_key,
        status=_snapshot_status_value(snapshot.status),
        captured_at=snapshot.captured_at,
        snapshot_json=snapshot.to_json_dict(),
        model_versions_json=snapshot.model_versions_json,
        warnings_json=snapshot.warnings_json,
    )
    session.add(record)
    return record


def persist_combo_ticket_with_snapshots(
    session: Session,
    ticket: ComboTicketCandidate,
    *,
    captured_at: datetime,
    model_versions_json: dict | None = None,
    snapshot_types: tuple[str, ...] = ("generated", "scored", "policy_decided"),
) -> db_models.ComboTicket:
    record = persist_combo_ticket_candidate(
        session,
        ticket,
        model_versions_json=model_versions_json,
    )
    session.flush()
    for snapshot_type in snapshot_types:
        persist_combo_ticket_snapshot(
            session,
            ComboTicketSnapshot(
                ticket_key=ticket.ticket_key,
                status=snapshot_type,
                candidate=ticket,
                captured_at=captured_at,
                model_versions_json=model_versions_json or {},
                warnings_json=[*ticket.warnings, f"snapshot_type:{snapshot_type}"],
            ),
            ticket_id=record.id,
        )
    return record


def persist_combo_leg_snapshot(
    session: Session,
    snapshot: ComboLegSnapshot,
    *,
    ticket_id: int | None = None,
    captured_at: datetime | None = None,
) -> db_models.ComboTicketSnapshot:
    record = db_models.ComboTicketSnapshot(
        ticket_id=ticket_id,
        ticket_key=snapshot.ticket_key,
        status="LEG_SNAPSHOT",
        captured_at=captured_at or snapshot.captured_at,
        snapshot_json=snapshot.to_json_dict(),
        model_versions_json=snapshot.model_versions_json,
        warnings_json=snapshot.warnings_json,
    )
    session.add(record)
    return record


def _snapshot_status_value(status: object) -> str:
    value = getattr(status, "value", status)
    return str(value)
