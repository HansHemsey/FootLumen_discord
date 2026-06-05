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
            f"Date : {ticket.combo_date.isoformat()}",
            f"Session : {ticket.session_key}",
            f"Premier kickoff : {_dt(ticket.first_kickoff_at, self.timezone)}",
            f"Lock prévu : {_dt(ticket.lock_time, self.timezone)}",
            "",
            "Legs :",
            *_staff_leg_lines(ticket),
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
            f"Date : {ticket.combo_date.isoformat()}",
            f"Session : {ticket.session_key}",
            f"Verrouillé à : {_dt(locked_at, self.timezone)}",
            f"Premier kickoff : {_dt(ticket.first_kickoff_at, self.timezone)}",
            "",
            "Legs :",
            *_public_leg_lines(ticket),
            "",
            f"Cote combinée : {ticket.combined_decimal_odds:.2f}",
            f"Proba ajustée : {_pct(ticket.combined_probability_adjusted)}",
            f"Fair odds : {ticket.combined_fair_odds:.2f}",
            f"EV ajustée : {_pct(ticket.combined_ev_adjusted)}",
            "Confiance ticket : "
            f"{ticket.combined_confidence_label} ({ticket.combined_confidence_score:.1f})",
            "",
            "État données :",
            *_data_state_lines(ticket),
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
                    "",
                    "Legs audit :",
                    *_staff_leg_lines(ticket),
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


def _public_leg_lines(ticket: ComboTicketCandidate) -> list[str]:
    lines: list[str] = []
    for index, leg in enumerate(ticket.legs, start=1):
        match_label = leg.match_label or _fallback_match_label(leg)
        odd = leg.executable_decimal_odd or leg.decimal_odd
        market_probability = (
            leg.market_probability_consensus
            if leg.market_probability_consensus is not None
            else leg.market_probability
        )
        bookmaker = leg.bookmaker_name or "consensus"
        kickoff = leg.kickoff_display or _dt(leg.kickoff_at_utc, ZoneInfo("Europe/Paris"))
        lines.append(
            f"{index}. {match_label} ({kickoff})"
        )
        lines.append(
            f"   Sélection : {leg.selection} @ {odd:.2f} ({bookmaker})"
        )
        lines.append(
            f"   P modèle {_pct(leg.model_probability)} | marché {_pct(market_probability)} "
            f"| edge {_pct(leg.edge)} | EV {_pct(leg.ev)}"
        )
    return lines


def _staff_leg_lines(ticket: ComboTicketCandidate) -> list[str]:
    lines: list[str] = []
    for index, leg in enumerate(ticket.legs, start=1):
        match_label = leg.match_label or _fallback_match_label(leg)
        odd = leg.executable_decimal_odd or leg.decimal_odd
        bookmaker = leg.bookmaker_name or "consensus"
        lines.append(
            f"{index}. {match_label} — {leg.selection} @ {odd:.2f} ({bookmaker})"
        )
        lines.append(
            f"   fixture_id={leg.fixture_id} prediction_snapshot_id="
            f"{leg.prediction_snapshot_id or 'n.d.'} odds_snapshot_id="
            f"{leg.odds_snapshot_id or 'n.d.'}"
        )
        lines.append(
            f"   P modèle {_pct(leg.model_probability)} | edge {_pct(leg.edge)} | "
            f"EV {_pct(leg.ev)} | data {leg.data_quality_score:.0f}/100 | "
            f"lineups {_lineup_state(leg.lineup_status)}"
        )
        for warning in leg.warnings[:4]:
            lines.append(f"   warning={warning}")
    return lines


def _data_state_lines(ticket: ComboTicketCandidate) -> list[str]:
    if not ticket.legs:
        return ["- n.d."]
    min_quality = min(leg.data_quality_score for leg in ticket.legs)
    odds_fresh = all(
        leg.odds_last_update is not None
        and "odds_stale" not in leg.warnings
        and "odds_freshness_unknown" not in leg.warnings
        for leg in ticket.legs
    )
    lineup_states = sorted({_lineup_state(leg.lineup_status) for leg in ticket.legs})
    return [
        f"- Odds : {'fraîches' if odds_fresh else 'à surveiller'}",
        f"- Lineups : {', '.join(lineup_states)}",
        f"- Data quality min : {min_quality:.0f}/100",
    ]


def _fallback_match_label(leg) -> str:
    if leg.home_team_name and leg.away_team_name:
        return f"{leg.home_team_name} vs {leg.away_team_name}"
    return f"Fixture {leg.fixture_id}"


def _lineup_state(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized == "available":
        return "confirmées"
    if normalized == "partial":
        return "partielles"
    if normalized == "missing":
        return "non attendues/non disponibles"
    return "n.d."


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
