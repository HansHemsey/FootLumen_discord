"""Controlled Discord publication service for World Cup combo tickets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db.models import ComboTicket, DiscordMessage
from football_predictor.discord.service import DiscordDeliveryService, DiscordSendResult
from football_predictor.world_cup_combos.config import WorldCupComboConfig
from football_predictor.world_cup_combos.enums import ComboTicketStatus
from football_predictor.world_cup_combos.models import ComboTicketCandidate
from football_predictor.world_cup_combos.worldcup_combo_formatter import WorldCupComboFormatter
from football_predictor.world_cup_combos.worldcup_combo_publication_policy import (
    WorldCupComboPublicationPolicy,
)


@dataclass(frozen=True)
class ComboPublicationResult:
    status: str
    channel_key: str | None
    message_type: str
    ticket_key: str | None
    discord_message_id: int | None = None
    reason: str | None = None


class WorldCupComboPublicationService:
    def __init__(
        self,
        session: Session,
        config: WorldCupComboConfig,
        *,
        delivery_service: DiscordDeliveryService | None = None,
        formatter: WorldCupComboFormatter | None = None,
        staff_channel_key: str | None = None,
        public_channel_key: str | None = None,
    ) -> None:
        self.session = session
        self.config = config
        self.delivery_service = delivery_service
        self.formatter = formatter or WorldCupComboFormatter(config.timezone_display)
        self.staff_channel_key = staff_channel_key or config.staff_channel_key
        self.public_channel_key = public_channel_key or config.public_channel_key
        self.policy = WorldCupComboPublicationPolicy(config)

    def publish_watchlist_staff(
        self,
        ticket: ComboTicketCandidate,
        *,
        dry_run: bool = True,
        execute: bool = False,
    ) -> ComboPublicationResult:
        if not self.config.enabled:
            return ComboPublicationResult(
                status="skipped",
                channel_key=None,
                message_type="worldcup_combo_watchlist",
                ticket_key=ticket.ticket_key,
                reason="feature_disabled",
            )
        return self._send(
            ticket=ticket,
            markdown=self.formatter.format_watchlist_staff(ticket),
            channel_key=self.staff_channel_key,
            message_type="worldcup_combo_watchlist",
            dry_run=dry_run or not execute,
            execute=execute,
            target_status=ComboTicketStatus.WATCHLIST_STAFF,
        )

    def publish_locked(
        self,
        ticket: ComboTicketCandidate,
        *,
        locked_at: datetime,
        dry_run: bool = True,
        execute: bool = False,
    ) -> ComboPublicationResult:
        if not self.config.enabled:
            return ComboPublicationResult(
                status="skipped",
                channel_key=None,
                message_type="worldcup_combo_locked",
                ticket_key=ticket.ticket_key,
                reason="feature_disabled",
            )
        policy_ticket = self.policy.decide(ticket)
        if (
            ticket.publication_decision == ComboTicketStatus.LOCKED
            and policy_ticket.publication_decision == ComboTicketStatus.PUBLIC_PUBLISHED
        ):
            if self.config.staff_only_shadow_mode:
                return self._send(
                    ticket=policy_ticket,
                    markdown=self.formatter.format_watchlist_staff(policy_ticket),
                    channel_key=self.staff_channel_key,
                    message_type="worldcup_combo_staff",
                    dry_run=dry_run or not execute,
                    execute=execute,
                    target_status=ComboTicketStatus.STAFF_ONLY,
                )
            public_result = self._send(
                ticket=policy_ticket,
                markdown=self.formatter.format_public_locked(policy_ticket, locked_at=locked_at),
                channel_key=self.public_channel_key,
                message_type="worldcup_combo_public",
                dry_run=dry_run or not execute,
                execute=execute,
                target_status=ComboTicketStatus.PUBLIC_PUBLISHED,
            )
            if self.config.mirror_public_to_staff:
                self._send(
                    ticket=policy_ticket,
                    markdown=self.formatter.format_watchlist_staff(policy_ticket),
                    channel_key=self.staff_channel_key,
                    message_type="worldcup_combo_staff_mirror",
                    dry_run=dry_run or not execute,
                    execute=execute,
                    target_status=ComboTicketStatus.PUBLIC_PUBLISHED,
                    mark_ticket=False,
                )
            return public_result
        return self._send(
            ticket=ticket,
            markdown=self.formatter.format_watchlist_staff(policy_ticket),
            channel_key=self.staff_channel_key,
            message_type="worldcup_combo_staff",
            dry_run=dry_run or not execute,
            execute=execute,
            target_status=ComboTicketStatus.STAFF_ONLY,
        )

    def publish_no_bet(
        self,
        *,
        reason: str,
        ticket: ComboTicketCandidate | None = None,
        dry_run: bool = True,
        execute: bool = False,
    ) -> ComboPublicationResult:
        if not self.config.enabled:
            return ComboPublicationResult(
                status="skipped",
                channel_key=None,
                message_type="worldcup_combo_no_bet",
                ticket_key=ticket.ticket_key if ticket else None,
                reason="feature_disabled",
            )
        channel_key = (
            self.public_channel_key if self.config.publish_no_bet_public else self.staff_channel_key
        )
        return self._send(
            ticket=ticket,
            markdown=self.formatter.format_no_bet(reason=reason, ticket=ticket),
            channel_key=channel_key,
            message_type="worldcup_combo_no_bet",
            dry_run=dry_run or not execute,
            execute=execute,
            target_status=ComboTicketStatus.NO_BET,
            idempotency_seed=f"no_bet:{reason}:{ticket.ticket_key if ticket else 'none'}",
        )

    def _send(
        self,
        *,
        ticket: ComboTicketCandidate | None,
        markdown: str,
        channel_key: str,
        message_type: str,
        dry_run: bool,
        execute: bool,
        target_status: ComboTicketStatus,
        idempotency_seed: str | None = None,
        mark_ticket: bool = True,
    ) -> ComboPublicationResult:
        ticket_key = ticket.ticket_key if ticket else idempotency_seed
        idempotency_key = _idempotency_key(
            seed=ticket_key or "unknown",
            target_status=target_status,
            channel_key=channel_key,
            message_type=message_type,
        )
        if (
            ticket_key
            and self._existing_message(
                idempotency_key,
                message_type,
                channel_key=channel_key,
                include_dry_run=dry_run,
            )
            is not None
        ):
            return ComboPublicationResult(
                status="duplicate_skipped",
                channel_key=channel_key,
                message_type=message_type,
                ticket_key=ticket_key,
            )
        if self.delivery_service is None:
            return ComboPublicationResult(
                status="dry_run" if dry_run else "skipped",
                channel_key=channel_key,
                message_type=message_type,
                ticket_key=ticket_key,
                reason="no_delivery_service",
            )

        result = self.delivery_service.send_markdown(
            markdown,
            competition_key=self.config.competition_key,
            league_id=self.config.league_id,
            season=self.config.season,
            channel_key=channel_key,
            message_type=message_type,
            dry_run=dry_run,
            payload_metadata={
                "ticket_key": ticket_key,
                "combo_publication": True,
                "idempotency_key": idempotency_key,
                "publication_status": target_status.value,
                "publication_channel_key": channel_key,
            },
        )
        if execute and mark_ticket and ticket is not None:
            self._mark_ticket(ticket.ticket_key, target_status, result)
        return ComboPublicationResult(
            status=result.status,
            channel_key=channel_key,
            message_type=message_type,
            ticket_key=ticket_key,
            discord_message_id=result.discord_message_id,
        )

    def _existing_message(
        self,
        idempotency_key: str,
        message_type: str,
        *,
        channel_key: str,
        include_dry_run: bool,
    ) -> DiscordMessage | None:
        statuses = ("sent", "dry_run") if include_dry_run else ("sent",)
        stmt = select(DiscordMessage).where(
            DiscordMessage.message_type == message_type,
            DiscordMessage.channel_key == channel_key,
            DiscordMessage.status.in_(statuses),
        )
        for row in self.session.execute(stmt).scalars():
            payload = row.payload_json if isinstance(row.payload_json, dict) else {}
            if payload.get("idempotency_key") == idempotency_key:
                return row
        return None

    def _mark_ticket(
        self,
        ticket_key: str,
        status: ComboTicketStatus,
        result: DiscordSendResult,
    ) -> None:
        stmt = select(ComboTicket).where(ComboTicket.ticket_key == ticket_key)
        record = self.session.execute(stmt).scalars().first()
        if record is None:
            return
        payload: dict[str, Any] = (
            record.payload_json if isinstance(record.payload_json, dict) else {}
        )
        record.status = status.value
        record.publication_decision = status.value
        record.payload_json = {
            **payload,
            "publication": {
                "status": result.status,
                "discord_message_id": result.discord_message_id,
                "discord_api_message_id": result.discord_api_message_id,
                "channel_key": result.route.channel_key,
            },
        }


def _idempotency_key(
    *,
    seed: str,
    target_status: ComboTicketStatus,
    channel_key: str,
    message_type: str,
) -> str:
    return f"wc_combo:{seed}:{target_status.value}:{channel_key}:{message_type}"
