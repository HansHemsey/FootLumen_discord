"""Publication decision policy for World Cup combo tickets."""

from __future__ import annotations

from dataclasses import replace

from football_predictor.world_cup_combos.config import WorldCupComboConfig
from football_predictor.world_cup_combos.enums import ComboMarketScope, ComboTicketStatus
from football_predictor.world_cup_combos.models import ComboTicketCandidate

CRITICAL_WARNINGS = {
    "critical_risk",
    "market_scope_unknown",
    "unknown_market_scope",
    "same_fixture_conflict",
}


class WorldCupComboPublicationPolicy:
    """Decide whether a combo ticket is public, staff-only, or no-bet."""

    def __init__(self, config: WorldCupComboConfig) -> None:
        self.config = config

    def decide(self, ticket: ComboTicketCandidate) -> ComboTicketCandidate:
        status, reason = self._decision(ticket)
        warnings = list(ticket.warnings)
        if reason is not None and reason not in warnings:
            warnings.append(reason)
        return replace(
            ticket,
            publication_decision=status,
            no_publish_reason=reason if status != ComboTicketStatus.PUBLIC_PUBLISHED else None,
            warnings=warnings,
        )

    def _decision(
        self,
        ticket: ComboTicketCandidate,
    ) -> tuple[ComboTicketStatus, str | None]:
        if not self.config.enabled:
            return ComboTicketStatus.NO_BET, "feature_disabled"
        if ticket.legs_count == 0:
            return ComboTicketStatus.NO_BET, "no_legs"
        if ticket.combined_ev_adjusted <= 0:
            return ComboTicketStatus.NO_BET, "combined_ev_adjusted_non_positive"
        if ticket.combined_ev_adjusted < self.config.min_combined_ev_adjusted:
            return ComboTicketStatus.NO_BET, "combined_ev_adjusted_below_threshold"
        if any(leg.ev <= 0 for leg in ticket.legs):
            return ComboTicketStatus.NO_BET, "leg_ev_non_positive"
        if any(leg.edge <= 0 for leg in ticket.legs):
            return ComboTicketStatus.NO_BET, "leg_edge_non_positive"
        if any(leg.data_quality_score < self.config.min_leg_data_quality for leg in ticket.legs):
            return ComboTicketStatus.NO_BET, "data_quality_insufficient"
        if any(leg.market_scope == ComboMarketScope.UNKNOWN for leg in ticket.legs):
            return ComboTicketStatus.NO_BET, "market_scope_unknown"
        if CRITICAL_WARNINGS.intersection(ticket.warnings):
            return ComboTicketStatus.NO_BET, "critical_warning"

        public_blocker = self._public_blocker(ticket)
        if public_blocker is None:
            return ComboTicketStatus.PUBLIC_PUBLISHED, None
        return ComboTicketStatus.STAFF_ONLY, public_blocker

    def _public_blocker(self, ticket: ComboTicketCandidate) -> str | None:
        if self.config.staff_only_shadow_mode:
            return "staff_only_shadow_mode"
        if ticket.legs_count > self.config.max_public_legs:
            return "too_many_public_legs"
        if ticket.post_lock_risk_score > self.config.max_post_lock_risk_public:
            return "post_lock_risk_above_public_threshold"
        if ticket.combined_confidence_score < self.config.min_combined_confidence_public:
            return "combined_confidence_below_public_threshold"
        if "matchday3_public_risk" in ticket.warnings and not self.config.allow_public_matchday3:
            return "matchday3_public_forbidden"
        if "knockout_public_risk" in ticket.warnings and not self.config.allow_public_knockout:
            return "knockout_public_forbidden"
        if "same_group_matchday3_risk" in ticket.warnings:
            return "same_group_matchday3_risk"
        return None
