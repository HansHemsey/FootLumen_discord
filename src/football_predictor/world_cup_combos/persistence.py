"""Persistence helpers for World Cup combo tickets.

Sprint 1 keeps this module deliberately small: it creates the combo tables
idempotently and can persist domain snapshots, but it does not build, publish,
or settle combo tickets.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

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

CRITICAL_SNAPSHOT_PREFIXES = ("generated", "pre_lock", "locked", "published", "settled")
DEFAULT_SNAPSHOT_DUPLICATE_THROTTLE_MINUTES = 30


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
    throttle_minutes: int = DEFAULT_SNAPSHOT_DUPLICATE_THROTTLE_MINUTES,
) -> db_models.ComboTicketSnapshot:
    status = _snapshot_status_value(snapshot.status)
    snapshot_hash = _semantic_snapshot_hash(snapshot)
    if not _is_critical_snapshot_status(status):
        existing = _matching_recent_snapshot(
            session,
            ticket_key=snapshot.ticket_key,
            status=status,
            snapshot_hash=snapshot_hash,
            captured_at=snapshot.captured_at,
            throttle_minutes=throttle_minutes,
        )
        if existing is not None:
            return existing
    snapshot_json = snapshot.to_json_dict()
    snapshot_json["snapshot_hash"] = snapshot_hash
    record = db_models.ComboTicketSnapshot(
        ticket_id=ticket_id,
        ticket_key=snapshot.ticket_key,
        status=status,
        captured_at=snapshot.captured_at,
        snapshot_json=snapshot_json,
        model_versions_json=snapshot.model_versions_json,
        warnings_json=snapshot.warnings_json,
    )
    session.add(record)
    session.flush()
    return record


def persist_combo_ticket_with_snapshots(
    session: Session,
    ticket: ComboTicketCandidate,
    *,
    captured_at: datetime,
    model_versions_json: dict | None = None,
    snapshot_types: tuple[str, ...] = ("generated", "scored", "policy_decided"),
    snapshot_duplicate_throttle_minutes: int = DEFAULT_SNAPSHOT_DUPLICATE_THROTTLE_MINUTES,
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
            throttle_minutes=snapshot_duplicate_throttle_minutes,
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


def _is_critical_snapshot_status(status: str) -> bool:
    normalized = status.strip().lower()
    return normalized.startswith(CRITICAL_SNAPSHOT_PREFIXES)


def _matching_recent_snapshot(
    session: Session,
    *,
    ticket_key: str,
    status: str,
    snapshot_hash: str,
    captured_at: datetime,
    throttle_minutes: int,
) -> db_models.ComboTicketSnapshot | None:
    if throttle_minutes <= 0:
        return None
    cutoff = _as_utc(captured_at) - timedelta(minutes=throttle_minutes)
    rows = (
        session.query(db_models.ComboTicketSnapshot)
        .filter(
            db_models.ComboTicketSnapshot.ticket_key == ticket_key,
            db_models.ComboTicketSnapshot.status == status,
            db_models.ComboTicketSnapshot.captured_at >= cutoff,
        )
        .order_by(db_models.ComboTicketSnapshot.captured_at.desc())
        .all()
    )
    for row in rows:
        payload = row.snapshot_json if isinstance(row.snapshot_json, dict) else {}
        if payload.get("snapshot_hash") == snapshot_hash:
            return row
    return None


def _semantic_snapshot_hash(snapshot: ComboTicketSnapshot) -> str:
    payload = snapshot.candidate.to_json_dict()
    payload = _strip_volatile_snapshot_fields(payload)
    material: dict[str, Any] = {
        "status": _snapshot_status_value(snapshot.status),
        "candidate": payload,
        "model_versions_json": snapshot.model_versions_json,
        "warnings_json": snapshot.warnings_json,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _strip_volatile_snapshot_fields(value: Any) -> Any:
    volatile_keys = {"captured_at", "generated_at"}
    if isinstance(value, dict):
        return {
            key: _strip_volatile_snapshot_fields(item)
            for key, item in value.items()
            if key not in volatile_keys
        }
    if isinstance(value, list):
        return [_strip_volatile_snapshot_fields(item) for item in value]
    return value


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
