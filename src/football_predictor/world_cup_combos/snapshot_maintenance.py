"""Snapshot maintenance helpers for World Cup combo tickets."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import inspect, select

from football_predictor.db import models as db_models

CRITICAL_PREFIXES = ("generated", "pre_lock", "locked", "published", "settled")


@dataclass(frozen=True)
class SnapshotMaintenanceSummary:
    execute: bool
    total_snapshots: int
    duplicate_groups: int
    duplicate_rows: int
    deleted_rows: int
    proposed_duplicate_ids: list[int]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_combo_snapshots(session, *, execute: bool = False) -> SnapshotMaintenanceSummary:
    bind = session.get_bind()
    if not inspect(bind).has_table("combo_ticket_snapshots"):
        return SnapshotMaintenanceSummary(
            execute=execute,
            total_snapshots=0,
            duplicate_groups=0,
            duplicate_rows=0,
            deleted_rows=0,
            proposed_duplicate_ids=[],
        )
    rows = list(
        session.execute(
            select(db_models.ComboTicketSnapshot).order_by(
                db_models.ComboTicketSnapshot.ticket_key.asc(),
                db_models.ComboTicketSnapshot.status.asc(),
                db_models.ComboTicketSnapshot.captured_at.asc(),
                db_models.ComboTicketSnapshot.id.asc(),
            )
        ).scalars()
    )
    groups: dict[tuple[str, str, str], list[db_models.ComboTicketSnapshot]] = defaultdict(list)
    for row in rows:
        if _is_critical(row.status):
            continue
        payload = row.snapshot_json if isinstance(row.snapshot_json, dict) else {}
        snapshot_hash = payload.get("snapshot_hash")
        if not snapshot_hash:
            continue
        groups[(row.ticket_key, row.status, str(snapshot_hash))].append(row)

    duplicate_ids: list[int] = []
    duplicate_groups = 0
    for group_rows in groups.values():
        if len(group_rows) <= 1:
            continue
        duplicate_groups += 1
        duplicate_ids.extend(row.id for row in group_rows[1:])

    deleted_rows = 0
    if execute and duplicate_ids:
        for row_id in duplicate_ids:
            row = session.get(db_models.ComboTicketSnapshot, row_id)
            if row is not None:
                session.delete(row)
                deleted_rows += 1
        session.flush()

    return SnapshotMaintenanceSummary(
        execute=execute,
        total_snapshots=len(rows),
        duplicate_groups=duplicate_groups,
        duplicate_rows=len(duplicate_ids),
        deleted_rows=deleted_rows,
        proposed_duplicate_ids=duplicate_ids[:100],
    )


def _is_critical(status: str | None) -> bool:
    normalized = (status or "").strip().lower()
    return normalized.startswith(CRITICAL_PREFIXES)
