"""Discord delivery service with routing, dedupe and DB persistence."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from football_predictor.db.models import DiscordMessage, Fixture, ModelPrediction
from football_predictor.discord.config import DiscordChannelsConfig, DiscordWebhooksConfig
from football_predictor.discord.exceptions import DiscordWebhookError
from football_predictor.discord.formatter import format_prediction_markdown
from football_predictor.discord.router import DiscordRoute, resolve_discord_route
from football_predictor.discord.webhook import DiscordWebhookClient
from football_predictor.security.sanitize import (
    find_sensitive_data,
    sanitize_mapping,
    sanitize_text,
)
from football_predictor.utils.secrets import hash_secret
from football_predictor.utils.time import utc_now


@dataclass(frozen=True)
class DiscordSendResult:
    status: str
    route: DiscordRoute
    message_hash: str
    webhook_hash: str | None
    response_json: dict[str, object]
    discord_message_id: int | None
    discord_api_message_id: str | None = None


class DiscordDeliveryService:
    def __init__(
        self,
        session: Session,
        *,
        channels_config: DiscordChannelsConfig | None = None,
        webhooks_config: DiscordWebhooksConfig | None = None,
        legacy_webhook_url: str | None = None,
        timeout: float = 10.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.session = session
        self.channels_config = channels_config
        self.webhooks_config = webhooks_config
        self.legacy_webhook_url = legacy_webhook_url
        self.timeout = timeout
        self.http_client = http_client

    def send_markdown(
        self,
        markdown: str,
        *,
        competition_key: str | None = None,
        league_id: int | None = None,
        season: int | None = None,
        channel_key: str | None = None,
        message_type: str = "prediction",
        fixture_id: int | None = None,
        model_prediction_id: int | None = None,
        dry_run: bool = False,
        print_only: bool = False,
        force: bool = False,
        allow_discussions: bool = False,
        wait: bool = False,
        payload_metadata: dict[str, Any] | None = None,
    ) -> DiscordSendResult:
        route = resolve_discord_route(
            channels_config=self.channels_config,
            webhooks_config=self.webhooks_config,
            competition_key=competition_key,
            league_id=league_id,
            season=season,
            channel_key=channel_key,
            message_type=message_type,
            legacy_webhook_url=self.legacy_webhook_url,
            allow_discussions=allow_discussions,
            allow_missing_webhook=dry_run or print_only,
            force=force,
        )
        blocked_findings = find_sensitive_data(
            {"content": markdown, "payload_metadata": payload_metadata or {}},
            path="discord_message",
        )
        message_hash = hash_message(markdown)
        webhook_hash = route.webhook_hash
        if blocked_findings:
            row = self._persist_message(
                sanitize_text(markdown),
                route=route,
                message_hash=message_hash,
                status="blocked_secret",
                fixture_id=fixture_id,
                model_prediction_id=model_prediction_id,
                dry_run=dry_run,
                print_only=print_only,
                response_json={
                    "blocked_reason": "secret_detected",
                    "findings": [finding.as_dict() for finding in blocked_findings],
                },
                payload_metadata=payload_metadata,
            )
            self._result("blocked_secret", route, message_hash, row)
            raise DiscordWebhookError(
                "Discord message blocked by secret sanitizer",
                webhook_hash=webhook_hash,
                response_text=f"findings={len(blocked_findings)}",
            )
        if not force and webhook_hash is not None:
            existing = self._existing_sent(webhook_hash, message_hash)
            if existing is not None:
                row = self._persist_message(
                    markdown,
                    route=route,
                    message_hash=message_hash,
                    status="duplicate_skipped",
                    fixture_id=fixture_id,
                    model_prediction_id=model_prediction_id,
                    dry_run=dry_run,
                    print_only=print_only,
                    response_json={"duplicate_of": existing.id},
                    payload_metadata=payload_metadata,
                )
                return self._result("duplicate_skipped", route, message_hash, row)

        if print_only:
            row = self._persist_message(
                markdown,
                route=route,
                message_hash=message_hash,
                status="print_only",
                fixture_id=fixture_id,
                model_prediction_id=model_prediction_id,
                dry_run=dry_run,
                print_only=True,
                response_json={"print_only": True},
                payload_metadata=payload_metadata,
            )
            return self._result("print_only", route, message_hash, row)

        if dry_run:
            row = self._persist_message(
                markdown,
                route=route,
                message_hash=message_hash,
                status="dry_run",
                fixture_id=fixture_id,
                model_prediction_id=model_prediction_id,
                dry_run=True,
                print_only=False,
                response_json={"dry_run": True, "route": route.safe_dict()},
                payload_metadata=payload_metadata,
            )
            return self._result("dry_run", route, message_hash, row)

        if not route.webhook_url:
            raise DiscordWebhookError(
                "No Discord webhook configured "
                f"competition={route.competition_key} channel={route.channel_key}"
            )
        response = DiscordWebhookClient(
            route.webhook_url,
            timeout=self.timeout,
            client=self.http_client,
        ).send_markdown(markdown, wait=wait)
        row = self._persist_message(
            markdown,
            route=route,
            message_hash=message_hash,
            status="sent",
            fixture_id=fixture_id,
            model_prediction_id=model_prediction_id,
            dry_run=False,
            print_only=False,
            sent_at=utc_now(),
            response_json=response,
            payload_metadata=payload_metadata,
        )
        return self._result("sent", route, message_hash, row)

    def replace_previous_messages(
        self,
        *,
        competition_key: str | None = None,
        league_id: int | None = None,
        season: int | None = None,
        channel_key: str,
        message_type: str,
        dry_run: bool = False,
        print_only: bool = False,
        force: bool = False,
        payload_match: dict[str, object] | None = None,
    ) -> dict[str, object]:
        route = resolve_discord_route(
            channels_config=self.channels_config,
            webhooks_config=self.webhooks_config,
            competition_key=competition_key,
            league_id=league_id,
            season=season,
            channel_key=channel_key,
            message_type=message_type,
            legacy_webhook_url=self.legacy_webhook_url,
            allow_missing_webhook=dry_run or print_only,
            force=force,
        )
        rows = self._previous_sent_messages(route, payload_match=payload_match)
        deleted = 0
        missing_message_ids = 0
        errors: list[str] = []
        result: dict[str, object] = {
            "eligible": len(rows),
            "deleted": deleted,
            "missing_message_ids": missing_message_ids,
            "errors": errors,
        }
        if dry_run or print_only or not rows:
            return result
        if not route.webhook_url:
            errors.append("missing_webhook_url")
            return result
        client = DiscordWebhookClient(
            route.webhook_url,
            timeout=self.timeout,
            client=self.http_client,
        )
        for row in rows:
            message_id = discord_api_message_id(row)
            if message_id is None:
                missing_message_ids += 1
                continue
            try:
                response = client.delete_message(message_id)
            except DiscordWebhookError as exc:
                errors.append(sanitize_text(str(exc)))
                continue
            payload = row.payload_json if isinstance(row.payload_json, dict) else {}
            row.payload_json = sanitize_mapping({
                **payload,
                "deleted_replaced_at": utc_now().isoformat(),
                "delete_response": response,
            })
            row.status = "deleted_replaced"
            row.response_json = sanitize_mapping({
                **(row.response_json if isinstance(row.response_json, dict) else {}),
                "delete_response": response,
            })
            deleted += 1
        self.session.flush()
        result["deleted"] = deleted
        result["missing_message_ids"] = missing_message_ids
        return result

    def _existing_sent(self, webhook_hash: str, message_hash: str) -> DiscordMessage | None:
        stmt = select(DiscordMessage).where(
            DiscordMessage.webhook_hash == webhook_hash,
            DiscordMessage.message_hash == message_hash,
            DiscordMessage.status == "sent",
        )
        return self.session.execute(stmt).scalars().first()

    def _previous_sent_messages(
        self,
        route: DiscordRoute,
        *,
        payload_match: dict[str, object] | None = None,
    ) -> list[DiscordMessage]:
        self.session.flush()
        stmt = (
            select(DiscordMessage)
            .where(
                DiscordMessage.status == "sent",
                DiscordMessage.dry_run.is_(False),
                DiscordMessage.print_only.is_(False),
                DiscordMessage.channel_key == route.channel_key,
                DiscordMessage.message_type == route.message_type,
            )
            .order_by(DiscordMessage.created_at.asc())
        )
        if (
            route.competition_key is not None
            and route.competition_key not in {"global", "_global"}
            and route.league_id is None
        ):
            stmt = stmt.where(DiscordMessage.competition_key == route.competition_key)
        if route.league_id is not None:
            stmt = stmt.where(DiscordMessage.league_id == route.league_id)
        if route.season is not None:
            stmt = stmt.where(DiscordMessage.season == route.season)
        rows = list(self.session.execute(stmt).scalars())
        if not payload_match:
            return rows
        return [
            row
            for row in rows
            if all(
                (row.payload_json if isinstance(row.payload_json, dict) else {}).get(key)
                == value
                for key, value in payload_match.items()
            )
        ]

    def _persist_message(
        self,
        markdown: str,
        *,
        route: DiscordRoute,
        message_hash: str,
        status: str,
        fixture_id: int | None,
        model_prediction_id: int | None,
        dry_run: bool,
        print_only: bool,
        response_json: dict[str, Any],
        sent_at: datetime | None = None,
        payload_metadata: dict[str, Any] | None = None,
    ) -> DiscordMessage:
        webhook_hash = route.webhook_hash
        metadata = sanitize_mapping(payload_metadata or {})
        sanitized_markdown = sanitize_text(markdown)
        sanitized_response_json = sanitize_mapping(response_json)
        idempotency_key = metadata.get("idempotency_key")
        row = DiscordMessage(
            fixture_id=fixture_id,
            model_prediction_id=model_prediction_id,
            sent_at=sent_at,
            status=status,
            competition_key=route.competition_key,
            league_id=route.league_id,
            season=route.season,
            channel_key=route.channel_key,
            message_type=route.message_type,
            dry_run=dry_run,
            print_only=print_only,
            webhook_url_hash=webhook_hash,
            webhook_hash=webhook_hash,
            message_hash=message_hash,
            idempotency_key=str(idempotency_key) if idempotency_key else None,
            message_markdown=sanitized_markdown,
            route_json=route.safe_dict(),
            response_json=sanitized_response_json,
            payload_json={
                "content": sanitized_markdown,
                "discord_api_message_id": _response_message_id(sanitized_response_json),
                **metadata,
            },
            response_text=sanitize_text(str(sanitized_response_json)[:500])
            if sanitized_response_json
            else None,
        )
        self.session.add(row)
        self.session.flush()
        return row

    @staticmethod
    def _result(
        status: str,
        route: DiscordRoute,
        message_hash: str,
        row: DiscordMessage,
    ) -> DiscordSendResult:
        return DiscordSendResult(
            status=status,
            route=route,
            message_hash=message_hash,
            webhook_hash=hash_secret(route.webhook_url),
            response_json=row.response_json if isinstance(row.response_json, dict) else {},
            discord_message_id=row.id,
            discord_api_message_id=discord_api_message_id(row),
        )


def hash_message(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def discord_api_message_id(row: DiscordMessage) -> str | None:
    payload = row.payload_json if isinstance(row.payload_json, dict) else {}
    response = row.response_json if isinstance(row.response_json, dict) else {}
    value = payload.get("discord_api_message_id") or _response_message_id(response)
    return str(value) if value else None


def _response_message_id(response_json: dict[str, Any]) -> str | None:
    value = response_json.get("id") or response_json.get("message_id")
    return str(value) if value else None


def send_discord_message(
    service: DiscordDeliveryService,
    *,
    competition_key: str,
    channel_key: str,
    content: str,
    message_type: str,
    fixture_id: int | None = None,
    model_prediction_id: int | None = None,
    dry_run: bool = False,
    print_only: bool = False,
    force: bool = False,
    allow_discussions: bool = False,
) -> DiscordSendResult:
    return service.send_markdown(
        content,
        competition_key=competition_key,
        channel_key=channel_key,
        message_type=message_type,
        fixture_id=fixture_id,
        model_prediction_id=model_prediction_id,
        dry_run=dry_run,
        print_only=print_only,
        force=force,
        allow_discussions=allow_discussions,
    )


def send_prediction_to_discord(
    service: DiscordDeliveryService,
    model_prediction_id: int,
    *,
    dry_run: bool = False,
    print_only: bool = False,
    force: bool = False,
    timezone_name: str = "Europe/Paris",
) -> DiscordSendResult:
    prediction = service.session.get(ModelPrediction, model_prediction_id)
    if prediction is None:
        raise DiscordWebhookError(f"Unknown model_prediction_id={model_prediction_id}")
    fixture = service.session.get(Fixture, prediction.fixture_id)
    rendered_prediction = SimpleNamespace(
        predicted_outcome=prediction.predicted_outcome or prediction.predicted_result,
        probabilities={
            "p_home": prediction.p_home,
            "p_draw": prediction.p_draw,
            "p_away": prediction.p_away,
        },
        confidence_label=prediction.confidence_label,
        confidence_score=prediction.confidence_score,
        explanations=prediction.explanations_json or prediction.explanation_json or [],
        data_quality_json=prediction.data_quality_json or {},
        market_probabilities=None,
        key_absences_json={},
        match_label=f"{fixture.home_team} vs {fixture.away_team}" if fixture else None,
        competition=str(fixture.league_id) if fixture else None,
        match_date=fixture.date if fixture else None,
    )
    markdown = format_prediction_markdown(
        rendered_prediction,
        fixture,
        timezone_name=timezone_name,
    )
    return service.send_markdown(
        markdown,
        competition_key=None,
        league_id=fixture.league_id if fixture else None,
        season=fixture.season if fixture else None,
        channel_key="predictions",
        message_type="prediction",
        fixture_id=prediction.fixture_id,
        model_prediction_id=model_prediction_id,
        dry_run=dry_run,
        print_only=print_only,
        force=force,
    )


def send_standings_to_discord(service: DiscordDeliveryService, **kwargs: Any) -> DiscordSendResult:
    return service.send_markdown(message_type="standings", channel_key="classement", **kwargs)


def send_calendar_to_discord(service: DiscordDeliveryService, **kwargs: Any) -> DiscordSendResult:
    return service.send_markdown(message_type="calendar", channel_key="calendrier", **kwargs)


def send_daily_matches_to_discord(
    service: DiscordDeliveryService, **kwargs: Any
) -> DiscordSendResult:
    return service.send_markdown(
        message_type="daily_matches",
        channel_key="matchs_du_jour",
        **kwargs,
    )


def send_analysis_to_discord(service: DiscordDeliveryService, **kwargs: Any) -> DiscordSendResult:
    return service.send_markdown(message_type="analysis", channel_key="analyses", **kwargs)


def send_result_to_discord(service: DiscordDeliveryService, **kwargs: Any) -> DiscordSendResult:
    return service.send_markdown(message_type="result", channel_key="resultats", **kwargs)
