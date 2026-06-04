"""Markdown formatter for World Cup combo tickets."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from football_predictor.world_cup_combos.models import ComboTicketCandidate


class WorldCupComboFormatter:
    def __init__(self, timezone_name: str = "Europe/Paris") -> None:
        self.timezone = ZoneInfo(timezone_name)

    def format_watchlist_staff(self, ticket: ComboTicketCandidate) -> str:
        lines = [
            "```md",
            "🧾 COMBINÉ CDM — WATCHLIST STAFF",
            "",
            f"Session : {ticket.session_key}",
            f"Premier kickoff : {_dt(ticket.first_kickoff_at, self.timezone)}",
            f"Lock prévu : {_dt(ticket.lock_time, self.timezone)}",
            "",
            "Legs :",
            *_leg_lines(ticket),
            "",
            f"Cote combinée : {ticket.combined_decimal_odds:.2f}",
            f"EV ajustée : {_pct(ticket.combined_ev_adjusted)}",
            "Confiance ticket : "
            f"{ticket.combined_confidence_label} ({ticket.combined_confidence_score:.1f})",
            f"Décision actuelle : {ticket.publication_decision.value}",
            f"Raison : {ticket.no_publish_reason or 'n.d.'}",
            "",
            "Warnings :",
            *_warning_lines(ticket.warnings),
            "",
            "Note : High signifie qualité/value/risque maîtrisé, pas certitude de résultat.",
            "```",
        ]
        return _trim_markdown(lines)

    def format_public_locked(self, ticket: ComboTicketCandidate, *, locked_at: datetime) -> str:
        lines = [
            "```md",
            "🎯 COMBINÉ CDM — VERROUILLÉ",
            "",
            f"Verrouillé à : {_dt(locked_at, self.timezone)}",
            f"Premier kickoff : {_dt(ticket.first_kickoff_at, self.timezone)}",
            "",
            "Legs :",
            *_leg_lines(ticket),
            "",
            f"Cote combinée : {ticket.combined_decimal_odds:.2f}",
            f"Proba ajustée : {_pct(ticket.combined_probability_adjusted)}",
            f"Fair odds : {ticket.combined_fair_odds:.2f}",
            f"EV ajustée : {_pct(ticket.combined_ev_adjusted)}",
            "Confiance ticket : "
            f"{ticket.combined_confidence_label} ({ticket.combined_confidence_score:.1f})",
            f"Data quality min : {min(leg.data_quality_score for leg in ticket.legs):.0f}/100",
            "",
            "Note : pari combiné probabiliste. High = ticket propre/value positive/"
            "risque maîtrisé, pas une certitude.",
            "```",
        ]
        return _trim_markdown(lines)

    def format_no_bet(
        self,
        *,
        reason: str,
        ticket: ComboTicketCandidate | None = None,
    ) -> str:
        lines = [
            "```md",
            "🚫 Aucun combiné CDM publiable",
            "",
            f"Raison : {reason}",
        ]
        if ticket is not None:
            lines.extend(
                [
                    f"Meilleur ticket staff : {ticket.ticket_key}",
                    f"EV ajustée : {_pct(ticket.combined_ev_adjusted)}",
                    "Confiance : "
                    f"{ticket.combined_confidence_label} ({ticket.combined_confidence_score:.1f})",
                    "",
                    "Warnings :",
                    *_warning_lines(ticket.warnings),
                ]
            )
        lines.extend(
            [
                "",
                "Aucune proposition sans value suffisante et risque maîtrisé.",
                "```",
            ]
        )
        return _trim_markdown(lines)


def _leg_lines(ticket: ComboTicketCandidate) -> list[str]:
    lines: list[str] = []
    for index, leg in enumerate(ticket.legs, start=1):
        lines.append(
            f"{index}. Fixture {leg.fixture_id} — {leg.selection} "
            f"@ {leg.decimal_odd:.2f} | P modèle {_pct(leg.model_probability)} | "
            f"edge {_pct(leg.edge)} | EV {_pct(leg.ev)} | data {leg.data_quality_score:.0f}/100"
        )
    return lines


def _warning_lines(warnings: list[str]) -> list[str]:
    if not warnings:
        return ["- aucun"]
    return [f"- {warning}" for warning in warnings[:12]]


def _dt(value: datetime, timezone: ZoneInfo) -> str:
    return value.astimezone(timezone).strftime("%Y-%m-%d %H:%M %Z")


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _trim_markdown(lines: list[str]) -> str:
    content = "\n".join(lines)
    if len(content) <= 1900:
        return content
    return content[:1850].rstrip() + "\n...\n```"
